# Gateway Buffer Plugin for Product Intake

Use this when Feishu product intake needs to capture rapid ordinary product text/images/videos without spending a full LLM turn per message.

## Goal

During active intake states, ordinary product data should update the local task JSON deterministically and return a short acknowledgement. Control commands must continue to reach the agent so state transitions, review, finish, and upload remain governed by the normal workflow.

## Recommended Hook

Implement a Hermes user plugin that registers `pre_gateway_dispatch`.

The hook should return `{"action": "skip", "reason": "product intake buffer"}` only when all of these are true:

- Platform is Feishu.
- Message is ordinary product text or media.
- Message is not a control command such as `开始录入`, `下一个`, `录入结束`, `结束录入`, `确认上传`, `状态`, `查看当前`, `退出`, or `/...`.
- A local task for the sender is currently active in `COLLECTING_PRODUCTS` or `REVIEWING_PRODUCT`.
- The state update was scheduled or completed successfully.

Do not skip dispatch for messages outside active intake; otherwise the user can get silent drops.

## State Update Rules

- Locate the latest active task under the profile `intake-tasks/` for `operator.open_id == event.source.user_id`.
- Create `current_product` if missing, with `local_id` like `p001` and `status=EMPTY_DRAFT`.
- For ordinary text, append to `current_product.text_snippets[]`, rebuild `raw_description`, and set product status to `DRAFT`.
- For each media path in `event.media_urls`, copy it into `cache/<task_id>/<product_id>/<sequence>.<ext>` and append one `media[]` item with a monotonic `sequence`.
- Preserve every image and video separately; never replace earlier media with the latest message.
- Deduplicate replayed gateway events by `(message_id, resource_key)`, where `resource_key` should be the stable source path/file key rather than only `Path.stem`.
- Serialize concurrent writes with an async lock and write JSON atomically.

- Return a short ack with current product id, text count, image count, video count, and pending count.

## Control Words

Keep these routed to the agent, not the buffer:

```text
开始录入
下一个
下一件
本品完成
确认当前
录入结束
结束录入
确认上传
继续录入
查看当前
查看汇总
状态
退出
帮助
重新映射
确认映射
重试上传
查看失败
```

## Upload Execution Pattern

When the user sends `确认上传`, perform these deterministic steps before reporting success:

1. Run `tools/intake_cli.py preflight --task <task.json>` and stop if it reports blockers.
2. Mark the task upload status as `UPLOADING` before creating records so crash recovery can distinguish partial work.
3. Create records with non-attachment fields only, persist returned `record_id_list` back into each product, then upload attachments.
4. If the Base has separate image/video fields, upload image media to the image attachment field and video media to the video attachment field; use relative `--file ./cache/...` paths from the profile home/cache root to satisfy lark-cli safe-file checks.
5. After attachment upload, run `+record-get` with projected description/image/video fields and compare returned attachment counts with local `media[]` before declaring success.
6. Mark products and the task as `UPLOADED` only after read-back verification succeeds; otherwise keep `PARTIAL_UPLOADED` with retryable errors.

## Validation

Add focused unit tests for:

- Control words return `None` from the hook so the agent receives them.
- Ordinary text in an active task returns `skip`, updates `text_snippets[]`, and sends an ack.
- Image/video media appends to `media[]`, assigns sequence numbers, and writes files into the task cache.
- Existing `tools/intake_cli.py` tests still pass.

Verify the plugin is enabled in the target profile with `plugins.enabled` and restart that profile's gateway before testing in Feishu.
