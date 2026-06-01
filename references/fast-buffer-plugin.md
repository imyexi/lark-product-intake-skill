# Fast Gateway Buffer Plugin for Product Intake

Use this reference when a Feishu/Lark product intake assistant needs to collect rapid product text, images, or videos without starting a full LLM agent turn for every ordinary message.

## When to Use

- The intake workflow is already stateful and writes local JSON task files.
- Users send many product photos/videos in quick succession and the full agent loop is too slow or may miss ordering.
- Ordinary intake data should be acknowledged quickly, while control phrases such as `开始录入`, `下一个`, `录入结束`, and `确认上传` must still reach the normal agent flow.

## Recommended Hermes Pattern

1. Create a profile-local plugin under the assistant profile, for example:
   - `~/.hermes/profiles/product-uploader/plugins/product-intake-buffer/plugin.yaml`
   - `~/.hermes/profiles/product-uploader/plugins/product-intake-buffer/__init__.py`
2. Register a `pre_gateway_dispatch` hook.
3. In the hook, return `None` for:
   - non-Feishu events,
   - control phrases and slash commands,
   - messages without text/media,
   - sessions with no active intake task.
4. Only after confirming the message is ordinary intake data, schedule the state update and return `{"action": "skip", "reason": "product intake buffer"}` to prevent a full agent turn.
5. Serialize local JSON writes with an async lock and use atomic replace for persistence.
6. Append each media item to `current_product.media[]` with a stable `sequence`; never overwrite earlier media.
6. Append each media item to `current_product.media[]` with a stable `sequence`; never overwrite earlier media.
7. Deduplicate replayed gateway events by `(message_id, resource_key)` using a stable source path/file key so retries do not duplicate attachments.
8. Send a short deterministic acknowledgement containing current product id, text count, image count, video count, and pending count.

## Profile Enablement Gotcha

When enabling a profile-local plugin from a shell, set `HERMES_HOME` to the profile directory. `HERMES_PROFILE` alone may not affect code paths that resolve `get_hermes_home()`.

```bash
HERMES_HOME=/home/ubuntu/.hermes/profiles/product-uploader \
  python - <<'PY'
from hermes_cli.plugins_cmd import cmd_enable
cmd_enable('product-intake-buffer')
PY
```

Verify the plugin loads under that same profile:

```bash
HERMES_HOME=/home/ubuntu/.hermes/profiles/product-uploader python - <<'PY'
from hermes_cli.plugins import PluginManager
m = PluginManager()
m.discover_and_load(force=True)
print([p for p in m.list_plugins() if p.get('key') == 'product-intake-buffer'])
PY
```

## Validation Checklist

- Control text returns `None` from the hook and still reaches the agent.
- Ordinary text in `COLLECTING_PRODUCTS` creates/updates `current_product` and appends to `text_snippets`.
- Image/video messages copy local platform cache files into the intake cache and append `media[]` entries with increasing `sequence` values.
- Existing `tools/intake_cli.py` tests still pass.
- Restart the profile gateway and confirm the platform is connected before live testing.
