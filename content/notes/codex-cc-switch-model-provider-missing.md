---
title: CC Switch 切换供应商后 Codex 旧会话报 provider 缺失或上游 400
date: 2026-10-19
summary: CC Switch 每次切换都会重写 config.toml，历史会话引用的 provider 定义可能丢失；在同一会话里跨供应商续聊，还会把第三方格式的 reasoning 条目带给 OpenAI 触发 400。前者补定义即可，后者只能新开会话。
---

## 现象

切换 CC Switch 供应商后，Codex 会按不同情况报三类错误。

情况一，切到第三方（DeepSeek）后打开旧会话：

```text
ChatGPT can't load config.toml, so this chat can't resume.
Model provider `cc-switch-official` not found.
```

情况二，切回 OpenAI Official 后打开 DeepSeek 时期的会话：

```text
Model provider `custom` not found.
```

情况三，在同一个会话里切到官方模型 `gpt-6.1-sol` 后发送消息：

```text
CC Switch local proxy failed while handling Codex endpoint /responses.
Provider: OpenAI Official; model: gpt-6.1-sol; upstream_status: HTTP 400;
cause: Invalid 'input[7].content': array too long. Expected an array with
maximum length 0, but got an array with length 1 instead.
```

前两种是配置加载失败，会话根本打不开；第三种会话能打开，但请求被上游拒绝。

## 原因

Codex 会把 `model_provider_id` 持久化到会话里，恢复时必须能在当前 `config.toml` 找到同名的 `[model_providers.<id>]` 区块。本机引用 `cc-switch-official` 的会话有 215 条，引用 `custom` 的有 38 条，所以缺哪个都会影响一批历史会话。

CC Switch 在接管代理或热切换供应商时会重写 `~/.codex/config.toml`，只写当前供应商自己的 provider 定义：

- 第三方供应商模板写 `[model_providers.custom]`，因此切过去后 `cc-switch-official` 的旧会话缺定义；
- OpenAI Official 模板不写任何 `[model_providers.*]`，因此切回官方后 `custom` 的旧会话缺定义。

第三种 400 与 `config.toml` 无关，是**同一个会话跨供应商续聊**导致的历史条目不兼容。第三方模型返回的 reasoning 条目带有 `content` 数组，而 OpenAI 要求这类条目的 `content` 长度必须为 0。检查本机会话记录，第 7 个输入项正是 `reasoning` 且 `content` 长度为 1，与报错中的 `input[7].content` 对应。切到官方模型后重放这段历史，就被上游按 schema 拒绝（此结论来自会话记录与报错对照，未逐字段验证其他条目）。

## 解决方法

第 1 步，先备份配置：

```bash
cp -p ~/.codex/config.toml ~/.codex/config.toml.bak-$(date +%Y%m%d-%H%M%S)
```

第 2 步，在当前配置里补回缺失的同名别名（示例为 `cc-switch-official`，指向同一个本地代理）：

```toml
[model_providers.cc-switch-official]
name = "CC Switch Official"
base_url = "http://127.0.0.1:15721/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "PROXY_MANAGED"
```

第 3 步，防复发：把上面这段放进 CC Switch → Codex → 公共配置（数据库键为 `common_config_codex`），每次接管都会把它合并回 `config.toml`。

第 4 步，处理反向情况：在 CC Switch 的 **OpenAI Official 供应商配置**里追加 `[model_providers.custom]` 区块（同样指向 15721），这样切回官方账号时 DeepSeek 时期的会话也能加载。

第 5 步，处理 HTTP 400：不要在同一会话里跨供应商继续对话。切到官方模型时新建会话；需要接着旧上下文就切回原供应商。这类历史条目格式差异无法通过配置修复。

第 6 步，配置诊断使用 `codex doctor`；不存在 `codex debug config` 这个命令。

## 验证

- 把 `cc-switch-official` 加入公共配置并重启 CC Switch 后，接管重写的 `config.toml` 仍包含该区块，`codex doctor` 显示配置正常加载。
- 给 OpenAI Official 供应商补 `custom` 区块后，供应商配置与 live `config.toml` 均通过 TOML 解析，live 同时存在 `custom` 与 `cc-switch-official`。
- 400 的复现证据：同日 11:06 切到官方、11:54 切回 DeepSeek，期间在同一会话发送 `gpt-6.1-sol` 消息返回上述 400；该问题只能通过新开会话规避。

边界：CC Switch 升级后建议复查一次 `config.toml` 的合并行为；跨供应商会话的兼容性取决于上游 schema，官方未承诺可混用，升级后仍可能出现新的条目差异。
