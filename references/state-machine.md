# State Machine and Commands

## Task States

| State | Meaning | Primary Allowed Commands |
| --- | --- | --- |
| `IDLE` | No active intake task. | `开始录入`, `帮助` |
| `COLLECTING_TARGET` | Task exists and waits for a Feishu Base link. | Send table link, `退出`, `状态` |
| `VALIDATING_TARGET` | Parsing link, reading table list, or checking permissions. | `退出`, `状态` |
| `MAPPING_FIELDS` | Waiting for field mapping confirmation. | `确认映射`, `重新映射`, `退出`, `状态` |
| `COLLECTING_PRODUCTS` | Product text, images, and videos are being collected. | Send text/media, `下一个`, `查看当前`, `确认当前`, `录入结束`, `退出` |
| `REVIEWING_PRODUCT` | Agent is confirming the current product from all accumulated text and media. | `确认当前`, `补充信息`, `删除素材`, `下一个`, `录入结束`, `退出` |
| `READY_TO_UPLOAD` | Batch is finished and waiting for upload approval. | `确认上传`, `继续录入`, `查看汇总`, `重新映射`, `退出` |
| `UPLOADING` | Base records and attachments are being uploaded. | `状态` |
| `UPLOADED` | All records and attachments uploaded successfully. | `开始录入`, `查看汇总` |
| `PARTIAL_UPLOADED` | Some records or attachments failed. | `重试上传`, `查看失败`, `开始录入` |
| `ABORTED` | User exited the task. | `开始录入` |

## Product States

| State | Meaning |
| --- | --- |
| `EMPTY_DRAFT` | Current product has no text or media. `下一个` must not create a row. |
| `DRAFT` | Current product is collecting text and media. |
| `MEDIA_PENDING` | Product has media items still downloading or caching. |
| `READY_FOR_REVIEW` | Text and media have reached terminal download states and can be confirmed. |
| `SEALED` | Product is fixed for this batch after `下一个` or `录入结束`. |
| `UPLOADED` | Product record and all attachments uploaded. |
| `PARTIAL_FAILED` | Product row exists, but some fields or attachments failed. |
| `FAILED` | Product upload failed before a usable Base row was created. |

## Media States

Every image and video is a separate `media[]` item.

| State | Meaning |
| --- | --- |
| `RECEIVED` | Feishu message event has been received. |
| `DOWNLOADING` | Resource download is in progress. |
| `DOWNLOADED` | Local cache path exists and is ready for confirmation/upload. |
| `DOWNLOAD_FAILED` | Resource download failed and can be retried. |
| `UPLOADING` | Local file is being uploaded to the Base attachment field. |
| `UPLOADED` | Attachment upload succeeded. |
| `UPLOAD_FAILED` | Attachment upload failed and can be retried. |

## Commands and Aliases

| Command | Valid States | Action |
| --- | --- | --- |
| `开始录入` | `IDLE`, `UPLOADED`, `PARTIAL_UPLOADED`, `ABORTED` | Create a new task and enter `COLLECTING_TARGET`. |
| Send Base link | `COLLECTING_TARGET` | Parse Base token/table ID and enter `VALIDATING_TARGET`. |
| `确认映射` | `MAPPING_FIELDS` | Save field mapping and enter `COLLECTING_PRODUCTS`. |
| `重新映射` | `MAPPING_FIELDS`, `READY_TO_UPLOAD` | Re-read fields and update mapping. |
| Send text | `COLLECTING_PRODUCTS`, `REVIEWING_PRODUCT` | Append to current product text snippets. |
| Send image/video | `COLLECTING_PRODUCTS`, `REVIEWING_PRODUCT` | Append to current product `media[]`, assign sequence, enqueue cache download. |
| `查看当前`, `状态` | All states except `IDLE` | Return task state, current product number, text count, media counts, and pending work. |
| `确认当前` | `COLLECTING_PRODUCTS`, `REVIEWING_PRODUCT` | Confirm current product from all text and all media. |
| `下一个` | `COLLECTING_PRODUCTS`, `REVIEWING_PRODUCT` | Seal current non-empty product and create the next `EMPTY_DRAFT`. |
| `录入结束` / `结束录入` | `COLLECTING_PRODUCTS`, `REVIEWING_PRODUCT` | Seal current product and enter `READY_TO_UPLOAD`. |
| `继续录入` | `READY_TO_UPLOAD` | Return to `COLLECTING_PRODUCTS`. |
| `查看汇总` | `READY_TO_UPLOAD`, `UPLOADED`, `PARTIAL_UPLOADED` | Summarize products, media, mapping, and upload state. |
| `确认上传` | `READY_TO_UPLOAD` | Start Base record creation and attachment upload. |
| `重试上传` | `PARTIAL_UPLOADED` | Retry only failed rows or failed attachments. |
| `查看失败` | `PARTIAL_UPLOADED` | Show failed product IDs, fields, files, and error messages. |
| `退出` | All states except `UPLOADING` | Mark current task `ABORTED` and exit the flow. |
| `帮助` | Any state | Show available commands for the current state. |

## Command Priority

1. `退出`
2. `状态` / `查看当前`
3. `确认上传`
4. `录入结束`
5. `下一个`
6. `确认当前`
7. Text/media ingestion

Use command priority when a message contains both command-like text and product information. If the message is ambiguous, ask one short confirmation question instead of guessing.

## Transition Constraints

- `UPLOADING` is non-interruptible by `退出`; report that upload is in progress and show `状态`.
- `确认上传` is ignored outside `READY_TO_UPLOAD`.
- `下一个` from `EMPTY_DRAFT` keeps the same empty product and tells the user no product was created.
- `录入结束` from `EMPTY_DRAFT` finishes the batch without adding an empty row.
- A new `开始录入` never resumes an `ABORTED` task. It creates a fresh task.
