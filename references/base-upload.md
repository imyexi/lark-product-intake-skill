# Feishu Base Upload

## Test Base

Use this table link for validation:

```text
https://i1zdcv06pi.feishu.cn/base/D4Vjbv19WaVVTwsGKdJcsnt5neg?from=from_copylink
```

Human label:

```text
010-20260119【总】会员日货盘表
```

Base token:

```text
D4Vjbv19WaVVTwsGKdJcsnt5neg
```

## Link Parsing

- `/base/<token>` gives the Base token.
- Query parameter `table=<id>` gives a table ID if present.
- Query parameter `view=<id>` gives a view ID if present.
- If no table ID is present, list tables and ask the user which table to use.
- If the link is a `/wiki/<token>` link, resolve the wiki node and use `node.obj_token` only when `obj_type=bitable`.

## Required Field Mapping

Read fields before writing. Do not guess.

Minimum required mapping:

| Logical field | Required | Expected Base type |
| --- | --- | --- |
| `raw_description` | Yes | text or compatible rich text field |
| `attachments` | Yes | attachment field |

Recommended optional mapping:

| Logical field | Expected type |
| --- | --- |
| `batch_id` | text |
| `operator` | text or user/person field |
| `intake_time` | date/time |
| `upload_status` | single select or text |
| Parsed fields such as `price`, `category`, `color`, `size` | matching writable fields |

If the target table has separate image and video attachment fields, allow:

```json
{
  "image_attachments": "图片",
  "video_attachments": "视频"
}
```

Otherwise, write both images and videos to the same `attachments` field.

## Read Commands

Use user identity by default:

```bash
lark-cli base +table-list --base-token D4Vjbv19WaVVTwsGKdJcsnt5neg --offset 0 --limit 50 --as user
```

Then read fields:

```bash
lark-cli base +field-list --base-token D4Vjbv19WaVVTwsGKdJcsnt5neg --table-id <table_id> --offset 0 --limit 200 --as user
```

If `lark-cli` returns `hermes context detected but lark-cli is not bound to it`, do not continue with field guesses. Ask the operator to confirm the identity preset, then bind and authorize:

```bash
# Safer default if the operator is unsure:
lark-cli config bind --source hermes --identity bot-only

# Use only after explicit confirmation when user identity is needed for Base access:
lark-cli config bind --source hermes --identity user-default --force
lark-cli auth login --recommend
```

For `lark-cli auth login --recommend`, if the command prints a device verification URL and blocks, generate a QR code and send both the opaque URL and the QR image to the user. Do not open the URL with browser tools because authorization must happen in the user's browser. If the harness cannot safely keep the polling command alive, use the CLI's no-wait/device-code mode described by its output and resume after the user says authorization is complete.

If `need_user_authorization` reports missing `base:table:read`, ask the operator to authorize:

```bash
lark-cli auth login --scope "base:table:read"
```

If field listing is attempted with app/tenant credentials and Feishu returns `99991672 Access denied`, inspect `permission_violations` and surface the exact authorization scopes and Open Platform authorization URL from the API error. For Base field discovery, the durable scope set is typically one of:

```text
bitable:app:readonly
bitable:app
base:field:read
```

When the CLI wrapper is unavailable but app credentials are configured, a deterministic fallback is to call the OpenAPI directly: request `tenant_access_token` from `/open-apis/auth/v3/tenant_access_token/internal`, then call `/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields?page_size=100` with `Authorization: Bearer <tenant_access_token>`. Do not print app secrets or tenant tokens in logs or chat.

For product intake, default to a one-shot "smooth upload" scope bundle for new users so field discovery, record creation, attachment upload, and read-back verification do not fail one step at a time:

```bash
lark-cli auth login --scope "base:field:read base:table:read base:record:create base:record:update base:record:read docs:document.media:upload" --no-wait --json
```

Generate and display the QR code as described in `references/lark-cli-auth-device-flow.md`, then after the user confirms authorization continue with `lark-cli auth login --device-code <device_code>` before retrying only failed work. Keep focused missing-scope recovery for high-sensitivity/minimum-permission mode, but do not make it the default product-intake path.

Before `确认上传`, run the local preflight check when using `tools/intake_cli.py`:

```bash
python tools/intake_cli.py preflight --task <task.json>
```

The preflight must block upload when any sealed product lacks `raw_description`, any media is still `RECEIVED`/`DOWNLOADING`, or the task cache contains image/video files that are not registered in product `media[]`. Resolve or explicitly document the blocker before creating Base records.

After a successful write/upload, verify only the created record IDs with projected fields to avoid loading large cell values: `+record-get --record-id ... --field-id <description> --field-id <image_attachment> --field-id <video_attachment> --format json --as user`.

## Record Creation

Create records with writable non-attachment fields only. Batch creates must not exceed 200 rows per call.

Example shape:

```json
{
  "fields": ["产品说明", "批次ID", "上传状态"],
  "rows": [
    ["黑色牛仔裤，档口报价 68", "pi_20260530_103000", "待上传附件"]
  ]
}
```

Command:

```bash
lark-cli base +record-batch-create --base-token <base_token> --table-id <table_id> --json @batch-create.json --as user
```

`lark-cli` treats `@file` inputs as safe local files: use a relative path within the current working directory, e.g. `cd` to the task directory and pass `--json @./batch-create.json`. Absolute paths such as `@/home/.../batch-create.json` are rejected.

Persist returned `record_id_list` back to each product.

## Attachment Upload

Upload attachments after record creation. Note that current `lark-cli` safe-file validation may reject absolute `--file` paths. If that happens, run the upload command from a common cache/root directory and pass each attachment as a relative `./...` path instead of weakening file-safety checks.

Upload attachments after record creation:

```bash
lark-cli base +record-upload-attachment \
  --base-token <base_token> \
  --table-id <table_id> \
  --record-id <record_id> \
  --field-id <attachment_field_id_or_name> \
  --file <cache_path> \
  --as user
```

`+record-upload-attachment` appends one or more files to a cell. Repeat `--file` for grouped uploads; do not pass a `--name` flag unless the installed CLI version explicitly documents it.

Rules:

- Upload every `media[]` item with `download_status=DOWNLOADED`.
- Upload in product order, then media sequence order.
- Mark each media item `UPLOADED` or `UPLOAD_FAILED`.
- If some attachments fail, mark the product `PARTIAL_FAILED` and the task `PARTIAL_UPLOADED`.
- `重试上传` must retry only failed records and failed media items.
- After upload succeeds, do a read-back verification when possible: request `base:record:read` if missing, then read the created records with projections for the description/image/video fields and verify counts match local `media[]` counts before declaring final success.
- `lark-cli` safe-file validation also applies to `--file`: use relative file paths from a suitable working directory (for example `cd` to the cache root and pass `--file ./<task_id>/<product>/<file>`), not absolute cache paths.

## Local Task Shape

```json
{
  "task_id": "pi_20260530_103000_user123",
  "status": "COLLECTING_PRODUCTS",
  "created_at": "2026-05-30T10:30:00+08:00",
  "operator": {
    "open_id": "ou_xxx",
    "display_name": "采购员"
  },
  "target": {
    "base_token": "D4Vjbv19WaVVTwsGKdJcsnt5neg",
    "table_id": "tblxxx",
    "source_url": "https://i1zdcv06pi.feishu.cn/base/D4Vjbv19WaVVTwsGKdJcsnt5neg?from=from_copylink"
  },
  "field_mapping": {
    "raw_description": "产品说明",
    "attachments": "素材附件",
    "batch_id": "批次ID",
    "uploaded_status": "上传状态"
  },
  "products": [
    {
      "local_id": "p001",
      "status": "DRAFT",
      "raw_description": "黑色牛仔裤，档口报价 68",
      "text_snippets": ["黑色牛仔裤，档口报价 68"],
      "parsed_fields": {
        "颜色": "黑色",
        "品类": "牛仔裤",
        "报价": "68"
      },
      "media": [
        {
          "sequence": 1,
          "message_id": "om_xxx",
          "type": "image",
          "cache_path": "cache/pi_20260530_103000_user123/p001/001.jpg",
          "download_status": "DOWNLOADED",
          "upload_status": "PENDING"
        }
      ],
      "base_record_id": null,
      "upload_status": "PENDING"
    }
  ]
}
```
