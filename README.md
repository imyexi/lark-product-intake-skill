# Lark Product Intake Skill

This repository contains the `lark-product-intake` Skill for Codex and Hermes.

The Skill defines a stateful Feishu product intake workflow for buyers who collect product descriptions, images, and videos in mobile Feishu chat, then upload the confirmed batch to a Feishu Base table.

Default validation target:

```text
https://i1zdcv06pi.feishu.cn/base/D4Vjbv19WaVVTwsGKdJcsnt5neg?from=from_copylink
```

Human label:

```text
010-20260119【总】会员日货盘表
```

Core invariant: when users rapidly send multiple product images, confirmation and upload must use the current product's complete `media[]` list, not only the last image.
