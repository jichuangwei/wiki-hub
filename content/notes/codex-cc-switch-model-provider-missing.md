---
title: CC Switch 接管后 Codex 旧会话恢复报 Model provider not found
date: 2026-10-19
summary: CC Switch 接管代理时会重写 config.toml，只保留当前供应商的 provider 定义，历史会话引用的 cc-switch-official 因此丢失；补回同名区块可恢复，放进公共配置可避免复发。
---

## 现象

切换到 CC Switch 代理后，打开早前创建的 Codex 会话，桌面端提示：

```text
ChatGPT can't load config.toml, so this chat can't resume.
Model provider `cc-switch-official` not found.
```

同一个错误在 2026-09-18 出现过一次，当时补配置后恢复；2026-10-19 切换 CC Switch 后再次出现。

## 原因

Codex 会把 `model_provider_id` 持久化到会话记录里，恢复会话时必须能在当前 `config.toml` 中找到同名的 `[model_providers.<id>]` 区块。本机 `~/.codex/sessions` 与 `archived_sessions` 中，引用 `cc-switch-official` 的记录有 215 条，引用 `custom` 的只有 2 条，所以缺少 `cc-switch-official` 会影响绝大多数历史会话。

CC Switch 在接管 Codex 代理时会重写 `~/.codex/config.toml`。本次日志显示 10:13:33 出现 `Codex Live 配置已接管，代理地址: http://127.0.0.1:15721/v1`，配置文件随后被改写（mtime 10:16），改写后只剩当前供应商模板里的 `[model_providers.custom]`，`cc-switch-official` 区块被删除。

因此问题不在账号或网络，而是配置模板每次接管时只保留当前 provider 的映射，把历史会话依赖的别名清掉了。CC Switch 的供应商配置中写死了 `model_provider = "custom"`，额外添加的 `[model_providers.*]` 区块不会随模板保留（此条为根据配置内容与现象推断，未阅读其源码）。

## 解决方法

第 1 步，先备份配置：

```bash
cp -p ~/.codex/config.toml ~/.codex/config.toml.bak-$(date +%Y%m%d-%H%M%S)
```

第 2 步，在 `[model_providers.custom]` 之后补回同名别名，指向同一个本地代理：

```toml
[model_providers.cc-switch-official]
name = "CC Switch Official"
base_url = "http://127.0.0.1:15721/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "PROXY_MANAGED"
```

第 3 步，保存后重新打开会话；桌面端仍显示旧错误时，重启一次 Codex 桌面端再试。

第 4 步，防复发：把同一段配置放进 CC Switch → Codex → 公共配置（数据库键为 `common_config_codex`），让它随每次接管写回。若放入公共配置后仍被覆盖，则改为写进当前供应商自己的配置字段。

第 5 步，恢复后若报 `connection refused`，说明代理没在运行，检查 15721 端口即可，与 provider 配置无关。

配置诊断使用 `codex doctor`；不存在 `codex debug config` 这个命令。

## 验证

- `codex doctor` 输出 `config.toml parse ok`，配置可正常加载；其中的 `disable_response_storage is ignored` 告警与本文问题无关。
- `lsof -nP -iTCP:15721 -sTCP:LISTEN` 能看到 cc-switch 监听 `127.0.0.1:15721`。
- 重开会话后不再提示 provider 不存在。

边界：本次只验证了补回区块后配置解析通过；公共配置能否真正防复发，需要在下次切换供应商后复查 `config.toml` 是否仍包含该区块，尚未做切换实测。

相关经验笔记：[多账号使用 Codex 与 Claude Code：会话共享与切换边界](/practices/multi-account-codex-claude-session-sharing/)
