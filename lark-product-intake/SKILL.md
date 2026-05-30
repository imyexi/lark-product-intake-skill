---
name: lark-product-intake
description: Use when Codex or Hermes needs to run a Feishu/Lark product intake workflow: collect product descriptions, images, and videos from a buyer in chat, maintain a multi-turn local task state, confirm each product from all accumulated media rather than only the last image, map fields dynamically, and upload the finished batch to a Feishu Base table.
---

# Lark Product Intake

## Overview

Use this skill to guide a Hermes or Codex agent through offline market product intake in Feishu chat. The agent collects product text, images, and videos into a local batch task, confirms product records with the user, then uploads the confirmed batch to a Feishu Base table.

This skill is a workflow specification, not a single command. Load the references below only when the current step needs them.

## Required References

- Read `references/workflow.md` when designing or running the end-to-end conversation.
- Read `references/state-machine.md` before implementing command handling, task recovery, or product confirmation.
- Read `references/media-cache.md` before handling Feishu IM images, videos, ordering, deduplication, or local cache paths.
- Read `references/base-upload.md` before parsing Base links, mapping fields, creating records, or uploading attachments.
- Read `references/testing.md` before validating the skill, especially with the provided test Base.

## Operating Rules

1. Treat the task as stateful. Never infer the active product only from the latest message.
2. Append every received image and video to the current product's `media[]` with a stable sequence number. Do not overwrite previous media.
3. Confirm and parse a product from the full current product state: all text snippets plus all downloaded images and videos.
4. If media is still downloading, report the pending count and delay final confirmation until the media queue reaches a terminal state.
5. Start a new product only when the user says `下一个` or when a fresh task starts. Empty drafts must not become upload rows.
6. Upload only after the user says `录入结束` and then explicitly confirms upload.
7. Read the target Base table fields before writing. Do not guess field names.
8. Do not write attachment fields during record creation. Create records first, then upload each local image/video file to the mapped attachment field.
9. Keep a local JSON task record for audit, retry, and crash recovery.

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
