---
title: 多账号使用 Codex 与 Claude Code：会话共享与切换边界
date: 2026-10-19
summary: Codex 与 Claude Code CLI 的本地会话可以跨账号、跨 provider 共用，Claude Desktop 则按账号和组织隔离；本文对比三种存储模型，给出切换检查清单与选型建议。
---

## 先给结论

| 客户端 | 会话存储 | 换账号或 provider 后 |
|---|---|---|
| Codex App / CLI | `~/.codex/sessions`，本地按时间存 | 旧会话仍可见；provider 只是每条会话的标签 |
| Claude Code CLI | `~/.claude/projects/<cwd>`，本地按工作目录存 | 旧会话仍可见，但 `--resume` 列表按 cwd 分组 |
| Claude Desktop Code | 按 account / org 分目录 | 官方与 3P 是两套身份、两套数据根，互不可见 |

一句话：**本地优先的客户端可以跨账号共用一个历史库；账号目录型的客户端不行。**

## 三种存储模型

### Codex：本地优先

- 会话文件：`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
- 归档：`~/.codex/archived_sessions/`
- 每条会话记录 `model_provider_id`，但会话列表不按 provider 过滤
- 切换 provider 只改 `config.toml` 与本地代理，不换 `CODEX_HOME`

代价：恢复旧会话时，`config.toml` 里必须仍有它引用的 `[model_providers.<id>]` 区块；CC Switch 接管后若删掉了旧 provider，就会报 `Model provider not found`。

### Claude Code CLI：本地优先，按 cwd 分组

- 会话文件：`~/.claude/projects/<encoded-cwd>/*.jsonl`
- 账号与 provider 不参与目录划分；换 token 或 `ANTHROPIC_BASE_URL` 不影响历史
- 注意：`--resume` 选择器默认只列当前 cwd 的会话；跨目录可用 `--resume <session-id>`

### Claude Desktop：账号目录制

官方模式：

```text
~/Library/Application Support/Claude/claude-code-sessions/<accountUUID>/<orgUUID>/
~/Library/Application Support/Claude/local-agent-mode-sessions/<accountUUID>/<orgUUID>/
```

3P（CC Switch 代理）模式：

```text
~/Library/Application Support/Claude-3p/
```

3P 使用独立的 userData 和假身份（`cowork-3p@localhost`），官方账号的目录不会被扫描，所以不是“隐藏”，而是“不在同一个库里”。

## 能共用 vs 不能共用

能共用：

- 同一台机器、同一个 `CODEX_HOME` / `CLAUDE_CONFIG_DIR` 下的本地会话
- 不同账号、不同 provider 产生的本地历史（列表层面）
- 历史消息、工具调用记录和文件快照

不能共用：

- 云端内容：ChatGPT 云端任务、Claude.ai 网页会话
- 跨机器：需要手动同步
- 跨配置根：换 `CODEX_HOME` / `CLAUDE_CONFIG_DIR` 就是另一个库
- 跨客户端：Codex 读不了 Claude 的 JSONL，反之亦然
- Claude Desktop 官方 ↔ 3P：只能切模式

## 切换检查清单

切换前：

- 确认当前配置根：Codex 看 `CODEX_HOME`，Claude 看 `CLAUDE_CONFIG_DIR`
- 确认 Claude Desktop 模式：`claude_desktop_config.json` 里是否有 `"deploymentMode": "3p"`
- 备份 `~/.codex/config.toml` 和 `~/.claude/settings.json`

切换后：

- Codex：确认旧会话引用的 `[model_providers.*]` 仍在；`codex doctor` 能解析配置
- Claude CLI：在原来的项目目录里执行 `--resume`，或指定 session id
- Claude Desktop：确认进程使用的是 `Claude` 还是 `Claude-3p` 数据根
- 代理端口：`lsof -nP -iTCP:15721 -sTCP:LISTEN` 能看到监听

## 两个典型坑

- Codex 旧会话恢复报 `Model provider not found`：[CC Switch 接管后 Codex 旧会话恢复报 Model provider not found](/notes/codex-cc-switch-model-provider-missing/)
- Claude Desktop 接入 CC Switch 后官方会话消失：[Claude Desktop 接入 CC Switch 后看不到官方账号会话](/notes/claude-desktop-3p-official-sessions-missing/)

## 选型建议

| 需求 | 建议 |
|---|---|
| 官方账号与第三方模型来回切，且保留全部历史 | Codex 或 Claude Code CLI |
| 必须用 Claude Desktop 图形界面 | 接受 Official / 3P 二选一，按需切换 |
| 想跨机器同步历史 | 自行同步 `~/.codex/sessions`、`~/.codex/archived_sessions`、`~/.claude/projects` |
| 想让 Codex 与 Claude 互相读历史 | 不支持，只能手工导出或粘贴 |

## 边界

- 本文基于 2026-10-19 的 macOS 环境与当时的客户端版本
- 未验证不同版本下 3P 数据根命名是否变化
- 不要跨 Claude profile 拷贝会话文件，account / org 不匹配可能破坏索引
