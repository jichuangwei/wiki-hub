---
title: Codex 通过 CC Switch 切换 provider 的常见报错与处理
date: 2026-10-19
summary: CC Switch 每次切换 provider 都会重写 config.toml，历史会话可能因缺少 provider 定义打不开；跨供应商续聊同一会话还会因历史条目格式差异被上游拒绝。本文整理三类报错的原因、修复与使用边界。
---

## 现象

通过 CC Switch 切换 Codex 的 provider 后，常见三类错误。

情况一，切到第三方（如 DeepSeek）后打开旧会话，配置加载失败：

```text
ChatGPT can't load config.toml, so this chat can't resume.
Model provider `cc-switch-official` not found.
```

情况二，切回 OpenAI Official 后打开第三方时期的会话：

```text
Model provider `custom` not found.
```

情况三，在同一个会话里切到官方模型后发送消息，会话能打开但请求被上游拒绝：

```text
CC Switch local proxy failed while handling Codex endpoint /responses.
Provider: OpenAI Official; model: gpt-6.1-sol; upstream_status: HTTP 400;
cause: Invalid 'input[7].content': array too long. Expected an array with
maximum length 0, but got an array with length 1 instead.
```

## 原因

### 会话绑定 provider id

Codex 会把 `model_provider_id` 持久化到会话里，恢复时必须能在当前 `config.toml` 找到同名的 `[model_providers.<id>]` 区块。本机引用 `cc-switch-official` 的会话有 215 条，引用 `custom` 的有 38 条，缺哪个都会影响一批历史会话。

CC Switch 在接管代理或热切换 provider 时会重写 `~/.codex/config.toml`，只写当前供应商自己的定义：第三方模板写 `[model_providers.custom]`，官方模板不写任何 `[model_providers.*]`。因此切到谁，另一个 provider 的旧会话就缺定义。

### 历史条目按 provider 格式存储

第三类 400 与配置无关。第三方模型返回的 reasoning 条目带有 `content` 数组，OpenAI 要求这类条目的 `content` 长度为 0。检查本机会话记录，第 7 个输入项正是 `reasoning` 且 `content` 长度为 1，与报错中的 `input[7].content` 对应。

Codex 续聊时把历史原样重放给当前 provider，不会按新 provider 的 schema 重写条目；CC Switch 只做转发，也不做转换。因此跨 provider 续聊是否可行，取决于两边历史格式是否兼容（此结论来自会话记录与报错对照，未逐字段验证其他条目）。

## 解决方法

第 1 步，备份配置：

```bash
cp -p ~/.codex/config.toml ~/.codex/config.toml.bak-$(date +%Y%m%d-%H%M%S)
```

第 2 步，补回缺失的 provider 定义（以 `cc-switch-official` 为例，指向同一个本地代理）：

```toml
[model_providers.cc-switch-official]
name = "CC Switch Official"
base_url = "http://127.0.0.1:15721/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "PROXY_MANAGED"
```

第 3 步，防复发：把这段放进 CC Switch → Codex → 公共配置（数据库键 `common_config_codex`），每次接管都会合并回 `config.toml`。

第 4 步，处理反向缺失：在 CC Switch 的 OpenAI Official 供应商配置里追加 `[model_providers.custom]`（同样指向 15721），切回官方时第三方会话也能打开。

第 5 步，按 provider 分会话：不要在同一会话里跨供应商继续对话。切到官方模型时新建会话；需要旧上下文就先在原会话生成一段摘要，再粘贴到新会话。同一 provider 内换模型不受影响。

第 6 步，配置诊断使用 `codex doctor`；不存在 `codex debug config` 这个命令。

## 验证

- 把 `cc-switch-official` 加入公共配置并重启 CC Switch 后，接管重写的 `config.toml` 仍包含该区块，`codex doctor` 显示配置正常加载。
- 给 OpenAI Official 供应商补 `custom` 后，供应商配置与 live `config.toml` 均通过 TOML 解析，live 同时存在 `custom` 与 `cc-switch-official`。
- 400 的复现证据：同日 11:06 切到官方、11:54 切回 DeepSeek，期间在同一会话发送 `gpt-6.1-sol` 消息返回上述 400；新会话不受影响。

边界：CC Switch 升级后建议复查 `config.toml` 的合并行为；跨供应商会话的兼容性取决于上游 schema，官方未承诺可混用，升级后仍可能出现新的条目差异。
