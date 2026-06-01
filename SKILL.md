---
name: lark-product-intake
description: "Use when Codex or Hermes needs to run a Feishu/Lark product intake workflow: collect product descriptions, images, and videos from a buyer in chat, maintain a multi-turn local task state, confirm each product from all accumulated media rather than only the last image, map fields dynamically, and upload the finished batch to a Feishu Base table."
---

# Lark Product Intake

## Overview

Use this skill to guide a Hermes or Codex agent through offline market product intake in Feishu chat. The agent collects product text, images, and videos into a local batch task, confirms product records with the user, then uploads the confirmed batch to a Feishu Base table.

This skill is a workflow specification, not a single command. Load the references below only when the current step needs them.

## Required References

- Read `references/hermes-install.md` when installing or wiring this workflow into Hermes.
- Read `references/workflow.md` when designing or running the end-to-end conversation.
- Read `references/state-machine.md` before implementing command handling, task recovery, or product confirmation.
- Read `references/media-cache.md` before handling Feishu IM images, videos, ordering, deduplication, local cache paths, or recovering video files that were cached under the document cache.
- Read `references/media-placeholder-recovery.md` when Feishu/Hermes surfaces local `image_url` placeholders instead of fast-buffer acknowledgements; append every placeholder path to the current product state before replying.
- Read `references/base-upload.md` before parsing Base links, mapping fields, creating records, or uploading attachments.
- Read `references/lark-cli-auth-device-flow.md` when `lark-cli` is unbound, user authorization is needed, or Base scopes such as `base:field:read` are missing.
- Read `references/cli-usage.md` before using `tools/intake_cli.py` for local task updates.
- Read `references/testing.md` before validating the skill, especially with the provided test Base.
- Read `references/gateway-buffer-plugin.md` before implementing or debugging the Feishu gateway buffer that captures rapid product text/images/videos without invoking the full agent for every ordinary message.
- Read `references/fast-buffer-plugin.md` before implementing or changing a gateway-level buffer that captures rapid Feishu product text/images/videos without invoking a full agent turn.

## Operating Rules

1. Treat the task as stateful. Never infer the active product only from the latest message.
2. When the user says `开始录入`, respond with a concise Chinese intake-start prompt: confirm or request the target Base/table first, then ask for the first product text/media. Do not expose internal compaction notes, hidden state, or implementation chatter to the user.
3. Append every received image and video to the current product's `media[]` with a stable sequence number. Do not overwrite previous media.
4. Confirm and parse a product from the full current product state: all text snippets plus all downloaded images and videos.
5. If media is still downloading, report the pending count and delay final confirmation until the media queue reaches a terminal state.
6. Start a new product only when the user says `下一个` or when a fresh task starts. Empty drafts must not become upload rows.
7. Upload only after the user says `录入结束` and then explicitly confirms upload.
8. Read the target Base table fields before writing. Do not guess field names.
9. Do not write attachment fields during record creation. Create records first, then upload each local image/video file to the mapped attachment field.
10. Treat `结束录入` as a finish alias for `录入结束`; otherwise the phrase can be captured as product text and uploaded into the description field.
11. Keep a local JSON task record for audit, retry, and crash recovery.

## Default Test Target

Use this Base link for validation when the user asks to test the workflow:

`https://i1zdcv06pi.feishu.cn/base/D4Vjbv19WaVVTwsGKdJcsnt5neg?from=from_copylink`

Human label: `010-20260119【总】会员日货盘表`

The Base token is `D4Vjbv19WaVVTwsGKdJcsnt5neg`. Read `references/testing.md` for the exact validation commands and known authorization requirements.

## Minimal Success Criteria

- The agent can start, resume, abort, and finish a product intake task.
- The available commands and state transitions match `references/state-machine.md`.
- Rapidly sent images are preserved as separate `media[]` entries and included in confirmation.
- Dynamic field mapping identifies at least a text field for product notes and an attachment field for media.
- Upload creates Base records first and attaches all product media afterwards.
- Partial upload failures remain retryable from the local JSON task state.
- When video appears missing, follow `references/media-cache.md` before concluding Feishu did not receive it; check gateway video logs, cache roots, and append recovered videos to `media[]`.
