# Product Intake Workflow

## Conversation Goal

Help a buyer in an offline market capture products from mobile Feishu. The buyer can send product descriptions, images, and videos in any order. Hermes groups them into product records, confirms the batch, then uploads only after explicit user approval.

## End-to-End Flow

1. User says `开始录入`.
2. Create a local task JSON record with status `COLLECTING_TARGET`.
3. Ask the user to send the target Feishu Base link.
4. Parse the Base token and optional table ID, then enter `VALIDATING_TARGET`. If no table ID is present, list tables and ask the user to choose one.
5. Read fields from the chosen table and enter `MAPPING_FIELDS`.
6. Ask the user to map:
   - Required: raw product description field.
   - Required: product media attachment field.
   - Optional: batch ID, operator, intake time, upload status, parsed fields such as price or category.
7. After field mapping, enter `COLLECTING_PRODUCTS` and create an `EMPTY_DRAFT` current product.
8. For each incoming message:
   - Text: append to the current product's text snippets and update `raw_description`.
   - Image/video: append a media item, enqueue download, and keep its sequence number.
   - Command: route by the state machine.
9. After each non-command message, respond with the current product status:
   - Product number.
   - Text snippet count.
   - Image count.
   - Video count.
   - Downloaded and pending media counts.
10. On `下一个`, seal the current non-empty product and create a new `EMPTY_DRAFT`.
11. On `录入结束`, seal the current non-empty product and enter `READY_TO_UPLOAD`.
12. In `READY_TO_UPLOAD`, show a batch summary and ask the user to send `确认上传` or `继续录入`.
13. On `确认上传`, enter `UPLOADING`, create Base records, upload attachments, then mark the task as `UPLOADED` or `PARTIAL_UPLOADED`.
14. On `退出`, mark the active task as `ABORTED`. A later `开始录入` always creates a new task.

## Product Confirmation

Confirmation is product-level, not message-level.

When confirming a product, always include:
- All text snippets and the merged `raw_description`.
- The full `media[]` list sorted by `sequence`.
- Counts by type: images, videos, failed downloads, pending downloads.
- Any parsed fields derived from text or media.

Do not summarize or analyze only the latest image. If a buyer sends ten images quickly, the current product must have ten media items, and product confirmation must consider all ten.

If media is still downloading:
- Provide an interim status message.
- Do not perform final visual confirmation until all media is `DOWNLOADED`, `DOWNLOAD_FAILED`, or intentionally skipped by the user.

## Suggested User Messages

Start:

```text
已开始产品录入。请发送要上传的飞书多维表格链接。
```

After target validation:

```text
已识别目标表格。请确认字段映射：产品说明 -> <字段名>，素材附件 -> <字段名>。
```

After receiving media:

```text
已加入当前第 2 个产品：说明 1 条，图片 4 张，视频 1 个，5 个素材已缓存。
发送“下一个”开始新产品，或继续发送图片/说明。
```

When downloads are pending:

```text
已收到 3 张新图片，正在缓存。当前第 2 个产品：图片 7 张，其中 3 张未完成缓存。
```

Before upload:

```text
本批次共 8 个产品，图片 43 张，视频 5 个。发送“确认上传”后才会写入飞书表格。
```

Partial failure:

```text
上传部分完成：7 个产品成功，1 个产品有附件失败。可发送“查看失败”或“重试上传”。
```

## Out-of-Scope Behavior

- Do not create an upload row for an empty current product.
- Do not upload anything on `录入结束`; wait for `确认上传`.
- Do not delete local task JSON immediately after upload. Keep it for audit and retry.
