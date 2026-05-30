# Local Intake CLI Usage

## Purpose

`tools/intake_cli.py` is a deterministic local helper for updating product intake task JSON. It is useful for Hermes integration, local testing, and emergency manual recovery.

The CLI does not call Feishu Base. It only updates local task state and copies local media files into the cache layout documented in `media-cache.md`.

## Supported States

The CLI accepts tasks in these states:

- `COLLECTING_PRODUCTS`
- `READY_TO_UPLOAD`

Commands that continue intake require `COLLECTING_PRODUCTS`. `status` can inspect both supported states.

## Task File

Minimal task shape:

```json
{
  "task_id": "pi_20260530_120000_user",
  "status": "COLLECTING_PRODUCTS",
  "created_at": "2026-05-30T12:00:00+08:00",
  "updated_at": "2026-05-30T12:00:00+08:00",
  "operator": {
    "open_id": null,
    "display_name": null
  },
  "target": {
    "base_token": "D4Vjbv19WaVVTwsGKdJcsnt5neg",
    "table_id": "tblxxx",
    "view_id": null,
    "source_url": null
  },
  "field_mapping": {},
  "products": [],
  "current_product": null,
  "upload": {
    "status": "NOT_STARTED",
    "errors": []
  }
}
```

## Commands

### Add Text

```powershell
python tools/intake_cli.py add-text --task intake-tasks/demo.json --text "白水晶 12mm"
```

Behavior:

- Creates `current_product` if missing.
- Appends the text to `text_snippets[]`.
- Rebuilds `raw_description` from all snippets.
- Marks the product `DRAFT`.

### Add Media

```powershell
python tools/intake_cli.py add-media --task intake-tasks/demo.json --files image1.jpg image2.webp video1.mp4
```

Behavior:

- Copies each file to `cache/<task_id>/<product_id>/<sequence>.<extension>`.
- Assigns monotonic `sequence` numbers per product.
- Preserves the source file name in `original_name`.
- Marks each item `download_status=DOWNLOADED` and `upload_status=PENDING`.

Supported image extensions:

```text
.jpg .jpeg .png .webp .gif .bmp .tif .tiff .heic
```

Supported video extensions:

```text
.mp4 .mov .avi .mkv .webm .m4v
```

### Next Product

```powershell
python tools/intake_cli.py next --task intake-tasks/demo.json
```

Behavior:

- If the current product has text or media, seals it as `SEALED`.
- Creates the next `EMPTY_DRAFT` product.
- If the current product is empty, keeps the same empty product and does not create an upload row.

### Finish Intake

```powershell
python tools/intake_cli.py finish --task intake-tasks/demo.json
```

Behavior:

- Seals the current non-empty product.
- Sets task status to `READY_TO_UPLOAD`.
- Sets `current_product` to `null`.
- Does not write to Feishu Base.

### Status

```powershell
python tools/intake_cli.py status --task intake-tasks/demo.json
```

Behavior:

- Prints the task status.
- Prints current product or batch counts.

## Local Validation

Run the unit tests:

```powershell
python -m unittest discover -s tests
```

Expected output:

```text
Ran 5 tests

OK
```

Runtime files under `cache/`, `intake-tasks/`, and `__pycache__/` are ignored by git.
