# Hermes Installation Guide

## Purpose

Use this guide when installing the `lark-product-intake` workflow into Hermes. The Skill provides the conversation contract and reference documents; Hermes provides message handling, media download, model calls, tool execution, and Feishu access.

## Files Hermes Must Load

Install the whole `lark-product-intake/` directory, not only `SKILL.md`.

Required files:

- `SKILL.md`: top-level trigger, operating rules, and success criteria.
- `agents/openai.yaml`: default Hermes-facing display metadata and prompt.
- `references/workflow.md`: end-to-end conversation flow.
- `references/state-machine.md`: task, product, media states, and command routing.
- `references/media-cache.md`: media ordering, cache paths, and download barriers.
- `references/base-upload.md`: Base link parsing, field mapping, record creation, and attachment upload.
- `references/cli-usage.md`: optional local JSON task helper.
- `references/testing.md`: local and external validation checklist.

## Agent Prompt

Configure the Hermes agent to include this prompt:

```text
Use $lark-product-intake to collect product notes, images, and videos in Hermes, then upload the batch to a Feishu Base table.
```

The prompt must mention `$lark-product-intake` exactly so the Skill is loaded when the workflow starts.

## Runtime Requirements

Hermes must provide or allow:

- Receiving Feishu text, image, and video messages.
- Downloading Feishu image/video resources to local files.
- Reading and writing local JSON task files under `intake-tasks/`.
- Writing downloaded media under `cache/<task_id>/<product_id>/`.
- Running `lark-cli` as the Feishu user identity.
- Running Python 3 if Hermes delegates local task updates to `tools/intake_cli.py`.

Recommended local directories:

```text
intake-tasks/
cache/
```

These directories are runtime state and should not be committed.

## Feishu Authorization

At minimum, table discovery and field mapping need Base read permission:

```bash
lark-cli auth login --scope "base:table:read"
```

Upload also needs the write and attachment scopes required by the local Feishu app and `lark-cli` configuration. Validate the effective permissions with:

```bash
lark-cli base +table-list --base-token D4Vjbv19WaVVTwsGKdJcsnt5neg --offset 0 --limit 50 --as user
```

Then list fields for the selected table:

```bash
lark-cli base +field-list --base-token D4Vjbv19WaVVTwsGKdJcsnt5neg --table-id <table_id> --offset 0 --limit 200 --as user
```

## Hermes Wiring

Hermes should route messages by task state:

1. Load `$lark-product-intake` when the user starts intake.
2. Store one active task JSON per intake session.
3. Append text to the current product's `text_snippets[]`.
4. Append every image and video message to the current product's `media[]` immediately with a stable `sequence`.
5. Download media asynchronously, but do not do final product confirmation until all media have terminal download states.
6. Seal products only on `下一个` or `录入结束`.
7. Upload only after the user sends `确认上传`.

If Hermes uses `tools/intake_cli.py`, it can delegate deterministic local state updates for `add-text`, `add-media`, `next`, `finish`, and `status`.

## Smoke Test

After installation:

1. Send `开始录入`.
2. Send the default Base link from `testing.md`.
3. Confirm or adjust field mapping.
4. Send product text.
5. Send three images quickly.
6. Check that the current product has three `media[]` items with sequences `1`, `2`, and `3`.
7. Send `下一个`.
8. Check that product `p001` is `SEALED` and product `p002` is `EMPTY_DRAFT`.
9. Send `录入结束`.
10. Confirm that no Base write happens until `确认上传`.
