---
title: Claude Desktop 切到 3P 后看不到官方账号会话
date: 2026-10-19
summary: CC Switch 接管 Claude Desktop 时会切到 3P 部署，使用独立数据目录和假账号，官方账号的会话目录不会被扫描；切回 Claude Desktop Official 即可恢复，数据不会丢失。
---

## 现象

在 CC Switch 的 Claude Desktop 卡片里，把 provider 从「Claude Desktop Official」切到第三方供应商后，重新打开 Claude Desktop：

- 侧边栏里官方账号时期的 Code 会话全部消失；
- 同一时间 Codex 也走 CC Switch 本地代理，但 Codex 的旧线程仍然可见；
- 官方实例切换前的日志还显示 `Loaded 24 persisted sessions`（另有 25 个 archived deferred），说明会话并没有被删除。

## 原因

Claude Desktop 的官方模式按账号和组织分目录保存会话：

```text
~/Library/Application Support/Claude/claude-code-sessions/<accountUUID>/<orgUUID>/
~/Library/Application Support/Claude/local-agent-mode-sessions/<accountUUID>/<orgUUID>/
```

CC Switch 的代理接管会写入 3P profile，并把客户端切到 3P 部署模式。3P 模式使用另一套数据根和假身份：

```text
~/Library/Application Support/Claude-3p/
~/Library/Logs/Claude-3p/
```

3P 进程的实际环境（已脱敏）：

```text
ANTHROPIC_BASE_URL=http://127.0.0.1:15721/claude-desktop
CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST=1
CLAUDE_CODE_USER_EMAIL=cowork-3p@localhost
CLAUDE_CODE_ACCOUNT_UUID=46821014-...
CLAUDE_CODE_ORGANIZATION_UUID=00000000-0000-4000-8000-000000000001
```

3P 会话写入 `Claude-3p/local-agent-mode-sessions/46821014/00000000/...`，官方账号的目录不会被加载。CC Switch 日志同时会出现：

```text
Claude Desktop 3P profile '00000000-0000-4000-8000-000000157210' written for provider '<provider-id>'
```

配置文件 `~/Library/Application Support/Claude/claude_desktop_config.json` 会变成 `"deploymentMode": "3p"`。

因此这不是「会话被隐藏」或「被删除」，而是官方模式与 3P 模式使用了两套 userData、两套账号和两套会话库。

## 解决方法

1. 打开 CC Switch → **Claude Desktop** 卡片。
2. 切回 **Claude Desktop Official（官方）**。
3. 让 CC Switch 自动重启 Claude Desktop，或先完全退出当前 3P 实例再手动启动。

切回后：

- 官方账号的会话会重新出现在侧边栏；
- 3P 期间新建的会话留在 `Claude-3p`，不会出现在官方模式里，切回 3P 才能看到；
- 两个方向的会话都没有丢失。

## 验证

确认当前模式：

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json')
print(json.load(open(p)).get('deploymentMode'))
PY
```

`3p` 表示代理模式；切回官方后该字段应不再是 `3p`。

确认进程使用的数据根：

```bash
lsof -p "$(pgrep -f '/Applications/Claude.app/Contents/MacOS/Claude' | head -1)" \
  | grep -E 'Claude-3p|/Claude/' | head
```

官方模式下应看到 `~/Library/Application Support/Claude` 与 `~/Library/Logs/Claude`；3P 模式对应 `Claude-3p` 路径。

本机的会话文件数量对照（2026-10-19）：

| 位置 | 文件数 |
|---|---|
| `Claude/claude-code-sessions/<官方 account>/<org>` | 59 |
| `Claude/local-agent-mode-sessions/<官方 account>/<org>` | 264 |
| `Claude-3p/claude-code-sessions` | 17 |
| `Claude-3p/local-agent-mode-sessions` | 246 |

边界：

- 不要把 `Claude-3p` 里的会话文件拷到官方目录，account/org 不匹配，可能破坏会话索引；
- Claude Code CLI 的历史在 `~/.claude/projects`，与桌面端两套目录都不同，不受这里的模式切换影响；
- 以上基于本机当时的 Claude Desktop 与 CC Switch 版本，其他版本的 3P 数据根命名可能变化。

相关记录：[CC Switch 接管后 Codex 旧会话恢复报 Model provider not found](/notes/codex-cc-switch-model-provider-missing/)

相关经验笔记：[多账号使用 Codex 与 Claude Code：会话共享与切换边界](/practices/multi-account-codex-claude-session-sharing/)
