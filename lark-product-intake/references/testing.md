# Testing Guide

## Validation Target

Use this Feishu Base as the default external validation target:

```text
https://i1zdcv06pi.feishu.cn/base/D4Vjbv19WaVVTwsGKdJcsnt5neg?from=from_copylink
```

Label:

```text
010-20260119【总】会员日货盘表
```

Base token:

```text
D4Vjbv19WaVVTwsGKdJcsnt5neg
```

## CLI Authorization Check

Verify table access:

```bash
lark-cli base +table-list --base-token D4Vjbv19WaVVTwsGKdJcsnt5neg --offset 0 --limit 50 --as user
```

Known result in the initial development environment:

```json
{
  "ok": false,
  "identity": "user",
  "error": {
    "type": "api_error",
    "message": "API call failed: need_user_authorization (...)",
    "hint": "current command requires scope(s): base:table:read"
  }
}
```

Authorize before reading fields:

```bash
lark-cli auth login --scope "base:table:read"
```

After authorization, rerun table listing and then:

```bash
lark-cli base +field-list --base-token D4Vjbv19WaVVTwsGKdJcsnt5neg --table-id <table_id> --offset 0 --limit 200 --as user
```

## Conversation Scenarios

### Text First, Media Later

1. User: `开始录入`
2. User sends Base link.
3. User confirms field mapping.
4. User: `黑色牛仔裤，档口报价 68`
5. User sends two images.
6. Expected: current product has one text snippet and two `media[]` items.
7. User: `下一个`
8. Expected: product `p001` is `SEALED`; `p002` is `EMPTY_DRAFT`.

### Media First, Text Later

1. User sends three images.
2. User: `白色衬衫，报价 45`
3. Expected: all three images and the text belong to the same current product.

### Rapid Consecutive Images

1. In `COLLECTING_PRODUCTS`, user sends five images quickly.
2. Expected:
   - Five media rows exist.
   - Each has a distinct `sequence`.
   - Confirmation counts all five images.
   - Visual analysis does not only inspect the fifth image.

### Video Support

1. User sends one video and two images for a product.
2. Expected:
   - Video appears in `media[]` with `type=video`.
   - Upload sends video to the mapped attachment field.
   - If video analysis is unavailable, confirmation still lists the video as attached media.

### Pending Downloads

1. User sends several large videos.
2. User immediately says `下一个`.
3. Expected:
   - Current product is not silently confirmed from incomplete media.
   - Agent reports pending downloads or seals the product with `MEDIA_PENDING`.
   - Upload waits for terminal media states or asks the user to skip failed media.

### Upload Confirmation Gate

1. User says `录入结束`.
2. Expected: no Base write occurs yet.
3. User says `确认上传`.
4. Expected: Base record creation starts.

### Partial Upload Failure

1. Simulate one failed attachment upload.
2. Expected:
   - Task becomes `PARTIAL_UPLOADED`.
   - Failed media item is `UPLOAD_FAILED`.
   - `查看失败` lists the product and file.
   - `重试上传` retries only the failed item.

### Exit and Restart

1. User says `退出`.
2. Expected: task becomes `ABORTED`.
3. User says `开始录入`.
4. Expected: a new task ID is created; the old task is not resumed.

## Static Validation Checklist

- `SKILL.md` has only `name` and `description` in frontmatter.
- `agents/openai.yaml` default prompt explicitly mentions `$lark-product-intake`.
- State names in workflow docs match `state-machine.md`.
- Command names are consistent across references.
- The rapid image rule appears in `SKILL.md`, `workflow.md`, `state-machine.md`, and `media-cache.md`.
- Base attachment upload is documented as a second step after record creation.
