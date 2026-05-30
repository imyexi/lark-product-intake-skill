# Lark Product Intake Skill

This repository contains the `lark-product-intake` Skill for Codex and Hermes.

The workflow helps a buyer collect product descriptions, images, and videos in Feishu chat, keep a local task state, confirm product records, and upload the approved batch to a Feishu Base table.

## Core Invariants

- Preserve every rapidly sent image or video as a separate `media[]` item.
- Confirm a product from all accumulated text snippets and media, not only the latest message.
- Never create upload rows for empty product drafts.
- Do not write to Feishu Base when the user says `录入结束`; wait for explicit `确认上传`.
- Create Base records first, then upload image and video attachments to the mapped attachment field.
- Keep local `intake-tasks/` JSON and `cache/` media files for audit, retry, and crash recovery.

## Hermes Quickstart

1. Copy the `lark-product-intake/` directory into the Hermes skill search path or package it with the Hermes agent bundle.
2. Ensure Hermes can read:
   - `lark-product-intake/SKILL.md`
   - `lark-product-intake/references/*.md`
   - `lark-product-intake/agents/openai.yaml`
3. Configure the Hermes agent prompt to include:

   ```text
   Use $lark-product-intake to collect product notes, images, and videos in Hermes, then upload the batch to a Feishu Base table.
   ```

4. Provision the runtime:
   - `lark-cli`
   - Python 3 for optional local state tooling
   - Writable `intake-tasks/` and `cache/` directories
   - Feishu user authorization for reading Base tables and writing records/attachments
5. Run a smoke test in Hermes:
   - User sends `开始录入`.
   - User sends the target Base link.
   - User sends a text product note.
   - User sends several images quickly.
   - Hermes reports all images in the current product's `media[]`.

Detailed installation notes are in `lark-product-intake/references/hermes-install.md`.

## Local CLI

`tools/intake_cli.py` is a deterministic local helper for updating intake task JSON during development or Hermes integration.

Run tests:

```powershell
python -m unittest discover -s tests
```

Example commands:

```powershell
python tools/intake_cli.py add-text --task intake-tasks/demo.json --text "白水晶 12mm"
python tools/intake_cli.py add-media --task intake-tasks/demo.json --files image1.jpg image2.jpg
python tools/intake_cli.py next --task intake-tasks/demo.json
python tools/intake_cli.py finish --task intake-tasks/demo.json
python tools/intake_cli.py status --task intake-tasks/demo.json
```

See `lark-product-intake/references/cli-usage.md` for the task shape and command behavior.

## Default Validation Target

Use this Feishu Base as the default external validation target:

```text
https://i1zdcv06pi.feishu.cn/base/D4Vjbv19WaVVTwsGKdJcsnt5neg?from=from_copylink
```

Base token:

```text
D4Vjbv19WaVVTwsGKdJcsnt5neg
```

Read `lark-product-intake/references/testing.md` before validating against the external Base, because user authorization is required.
