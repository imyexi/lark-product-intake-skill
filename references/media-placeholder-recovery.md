# Feishu Media Placeholder Recovery

Use this when Feishu/Hermes surfaces a placeholder such as "The user sent an image but I couldn't quite see it" with a local `image_url` path instead of the fast intake buffer acknowledging the media.

## Trigger

- The user sends one or more images/videos during `COLLECTING_PRODUCTS` or `REVIEWING_PRODUCT`.
- The assistant receives placeholder text containing local paths like:
  - `image_cache/img_<id>.jpg`
  - `cache/videos/video_<id>.mov`
- The current task JSON does not yet show the new media in `current_product.media[]`.

## Recovery Steps

1. Locate the latest active task JSON for the operator in `intake-tasks/` with status `COLLECTING_PRODUCTS` or `REVIEWING_PRODUCT`.
2. Read `current_product` and its existing `media[]`; do not infer product identity from only the newest placeholder.
3. For every placeholder path, verify the file exists locally.
4. Append each file as a separate `media[]` item with the next monotonic `sequence` for the current product.
5. Copy the file into `cache/<task_id>/<product_id>/<sequence>.<ext>` and record that path in `cache_path`.
6. Set `type=image` for image extensions and `type=video` for video extensions; set `download_status=DOWNLOADED`, `upload_status=PENDING`, and preserve the original path in `recovered_from`.
7. Update `updated_at`, save the task JSON atomically if possible, then reply with the current product text/image/video/pending counts.

## Pitfalls

- If placeholder text reached the agent, the fast buffer may not have handled that message. Do not just acknowledge from memory; inspect or update the JSON state.
- Multiple placeholders in one user message are multiple media items. Append all of them; never keep only the last image/video.
- Deduplicate by `recovered_from` or `cache_path` before appending, otherwise retries can duplicate media.
- Do not run vision analysis merely to ingest media. Vision is only needed when the workflow explicitly requires visual interpretation; intake only needs durable file capture.
- If a product text message also seems to have been missed, ask the user to resend or append it explicitly before sealing the product.
