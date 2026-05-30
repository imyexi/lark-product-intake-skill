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

If `need_user_authorization` reports missing `base:table:read`, ask the operator to authorize:

```bash
lark-cli auth login --scope "base:table:read"
```

For upload, the implementation also needs write and attachment scopes required by the local Feishu CLI/app configuration.

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

Persist returned `record_id_list` back to each product.

## Attachment Upload

Upload attachments after record creation:

```bash
lark-cli base +record-upload-attachment \
  --base-token <base_token> \
  --table-id <table_id> \
  --record-id <record_id> \
  --field-id <attachment_field_id_or_name> \
  --file <cache_path> \
  --name <display_name> \
  --as user
```

Rules:

- Upload every `media[]` item with `download_status=DOWNLOADED`.
- Upload in product order, then media sequence order.
- Mark each media item `UPLOADED` or `UPLOAD_FAILED`.
- If some attachments fail, mark the product `PARTIAL_FAILED` and the task `PARTIAL_UPLOADED`.
- `重试上传` must retry only failed records and failed media items.

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
