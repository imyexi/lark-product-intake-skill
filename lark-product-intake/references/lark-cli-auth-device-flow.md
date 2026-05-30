# Lark CLI Auth Device Flow for Product Intake

Use this when Base field discovery or upload fails because `lark-cli` is not bound or the user token lacks Base scopes.

## Binding

If `lark-cli base ... --as user` returns:

```text
hermes context detected but lark-cli is not bound to it
```

Do not guess the identity policy. Ask the user to confirm one of:

- `bot-only` for safer app/bot identity.
- `user-default` when the workflow needs the user's own Base permissions.

After confirmation, bind explicitly:

```bash
lark-cli config bind --source hermes --identity user-default --force
```

## Scope Recovery

For field discovery, a common missing scope is:

```text
base:field:read
```

Request only the missing scope instead of repeating a broad authorization:

```bash
lark-cli auth login --scope "base:field:read" --no-wait --json
```

The JSON includes `verification_url` and `device_code`. Generate and display a QR code before ending the turn:

```bash
lark-cli auth qrcode '<verification_url>' --output base_field_read_qrcode.png
```

Send the exact `verification_url` unchanged, then the QR image. Do not open the URL with browser tools; the user must authorize in their own browser.

When the user says authorization is complete, continue with the saved device code:

```bash
lark-cli auth login --device-code '<device_code>'
```

Use a long timeout (up to 600s) for the device-code polling command. After success, verify with:

```bash
lark-cli auth status
lark-cli base +field-list --base-token <base_token> --table-id <table_id> --offset 0 --limit 200 --as user
```

## Pitfalls

- Do not start a blocking `auth login --recommend` in the same turn after showing a URL; if it times out or is restarted, the device code can be invalidated.
- If a previous authorization process was killed, treat its URL/device code as stale and use the latest `--no-wait --json` output.
- If the user says they authorized but the scope is still missing, check `lark-cli auth status` first, then issue a focused scope request for the exact missing scope.
