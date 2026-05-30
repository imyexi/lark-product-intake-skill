# Media Cache

## Purpose

Feishu IM image and video messages must be downloaded to local cache before the product can be confirmed or uploaded to Base. The cache is also the retry source if Base attachment upload fails.

## Media Item Shape

```json
{
  "sequence": 1,
  "message_id": "om_xxx",
  "resource_key": "img_xxx_or_file_xxx",
  "type": "image",
  "mime_type": "image/jpeg",
  "original_name": "p001-001.jpg",
  "cache_path": "cache/pi_20260530_103000/p001/001.jpg",
  "received_at": "2026-05-30T10:30:05+08:00",
  "download_status": "DOWNLOADED",
  "upload_status": "PENDING",
  "error": null
}
```

## Ordering and Deduplication

- Assign `sequence` at ingestion time using a monotonic counter per product.
- Sort `media[]` by `sequence` for confirmation and upload.
- Deduplicate by `message_id` plus `resource_key`. If the same event is delivered twice, keep the first item and update its status only if needed.
- Never replace the current product's media list with the latest media message.

## Rapid Upload Handling

Mobile Feishu may deliver multiple images quickly while downloads finish out of order. The agent must:

1. Append all events immediately with `RECEIVED`.
2. Start downloads independently or via a bounded queue.
3. Preserve original `sequence` even if item 5 downloads before item 2.
4. Report pending counts after each burst.
5. Use a barrier before final product confirmation: all media must be `DOWNLOADED`, `DOWNLOAD_FAILED`, or explicitly skipped.

Correct behavior for five rapid images:

```json
"media": [
  {"sequence": 1, "message_id": "om_1", "download_status": "DOWNLOADED"},
  {"sequence": 2, "message_id": "om_2", "download_status": "DOWNLOADED"},
  {"sequence": 3, "message_id": "om_3", "download_status": "DOWNLOADED"},
  {"sequence": 4, "message_id": "om_4", "download_status": "DOWNLOADED"},
  {"sequence": 5, "message_id": "om_5", "download_status": "DOWNLOADED"}
]
```

Incorrect behavior:

```json
"image": {"message_id": "om_5"}
```

That loses four images and makes confirmation depend only on the last picture.

## Cache Path Convention

Use deterministic paths:

```text
cache/<task_id>/<product_local_id>/<sequence_padded>.<extension>
```

Examples:

```text
cache/pi_20260530_103000/p001/001.jpg
cache/pi_20260530_103000/p001/002.mp4
```

## Confirmation Input

When an AI model analyzes a product, pass:

- `raw_description`
- `text_snippets[]`
- Every downloaded image path in `media[]`
- Every downloaded video path or video metadata in `media[]`
- A list of failed or pending media items

If video analysis is not available, still keep the video as an attachment and mention it in confirmation.

## Cleanup

- Keep cache files for `UPLOADED` and `PARTIAL_UPLOADED` tasks until an explicit retention policy deletes them.
- Keep cache files for `ABORTED` tasks for debugging unless the user asks to clear them.
- Never delete cache files before Base attachment upload has succeeded.
