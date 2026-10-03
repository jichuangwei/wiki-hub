---
title: ChatGPT 云任务踩坑：用 Prompt 生成资讯，经 MCP 提交部署，再发送 HTML 邮件
date: 2026-10-04
summary: Prompt 负责内容和执行规则，MCP 提供发布能力，Actions 写入并部署；必须分别核验工具、归档、线上正文和邮件发送证据。
---

## 现象

希望每周一 09:00（Asia/Shanghai）自动生成上一完整自然周的 AI × Agent × 前端周报，提交到 Wiki Hub，部署 GitHub Pages，再通过 Gmail 密送完整 HTML 邮件。实际推进时，多次出现“HTML 生成了，网站没有更新”，以及网站更新后分类仍然错误的情况。

遇到的典型错误包括：

```text
发布工具未连接，未触发
This week already has a different publication; correction requires review
Repository access must be verified before replacement
Missing or out-of-order AI categories
```

连接 Auth0 时还曾遇到客户端未获准访问 resource server，以及 `no connections enabled for the client`。这些属于授权配置问题，不能靠修改周报正文解决。

本记录基于当前仓库实现与第 34–36 周的真实发布验收。三周发布已验证；该次执行没有发送历史周报邮件，也不能据此认定正式定时任务的 Gmail 链路已经验收。

## 原因

### 1. Prompt 描述动作，但不能凭空增加工具

最早的运行环境可以读取 GitHub Actions 状态或重跑旧 run，却没有发起新的 `workflow_dispatch` 的能力。把“提交并部署”写进 Prompt，不会自动获得这个入口。

需要检查任务实际可调用的工具，而不只看插件已安装、网页聊天连接成功或服务健康检查返回 200。普通聊天与定时任务都要在各自运行环境中验证。OpenAI 的[定时任务文档](https://learn.chatgpt.com/docs/automations)说明，网页任务可以使用该聊天可用的连接工具、技能和插件，但不会持续保留本机文件夹；所需资料应放在可访问的上传内容、项目或连接服务中。

### 2. 内容规则、客户端 schema 和服务端版本没有同步

旧规则只要求一个深度栏目，导致原有五类资讯被遗漏；有时把模型、产品和工程文章全部放进同一类。修正需要改正式 Skill，而不是每次对话临时解释分类。

另一个问题是服务端增加了 replacement 参数，当前会话看到的工具 schema 仍然只有 `start`、`end`、`html`。即使参数写进 Prompt，普通发布也不会变成审核更新。

第 34 周更新还真实触发了旧分类校验：仓库已接受六栏目，但 Railway Publisher 仍运行旧提交 `8f4f86d`，拒绝“五类资讯 + 深度资料”。部署当前代码 `4dddcc0` 后，同类 HTML 才能通过服务端校验。由此可见，仓库代码更新、服务部署和客户端工具发现是三个独立环节。

### 3. 生成、提交、部署与发信被混为一个状态

`publish_weekly_report` 返回 `request_id` 或 `dispatched`，只表示发布请求已创建或触发。归档 commit 已产生时，Pages 仍可能排队或失败；Pages 部署结束后，也要核对线上正文是否对应本次内容。

Publisher 不发送邮件。任务通知、邮件草稿、Gmail 连接成功及 Pages 成功都不能当作 HTML 邮件已发送的证据。

### 4. 同周重新生成会改变摘要，普通重试不能覆盖旧记录

Publisher 按周与 HTML 摘要处理幂等。相同内容可以安全复用；不同内容需要先查询旧记录，再根据状态选择审核替换。旧请求失败与旧请求已发布，所需条件不同。

上下文压缩还可能只留下“11,574 字符、校验通过”，却丢失完整 HTML。长度与摘要无法恢复原文；重新拼装会产生另一份正文。

## 解决方法

### 1. 明确各环节的职责

```text
每周定时触发
  → 云任务读取 main 的 Skill 与完整 HTML 模板
  → 核验本期资料，生成并保存完整 HTML
  → Publisher MCP 按周查询与发起发布
  → archive-report.yml 校验、归档、提交 main
  → 调用 pages.yml 部署指定归档 revision
  → 按 request_id 核验归档与线上正文
  → Gmail 工具发送相同 HTML，并保存发送证据
```

| 环节 | 实际职责 | 成功证据 |
|---|---|---|
| 云任务 Prompt / Skill | 周期、选题、分类、分析、排版及执行规则 | 完整 HTML、来源、模板 SHA |
| Publisher MCP | OAuth 校验、幂等、审核替换、触发 Actions、状态查询 | 本次 request_id |
| Archive Action | 校验并写入归档 | 真实 commit SHA、publication artifact |
| Pages workflow | 构建并部署指定 revision | 对应 Action 成功、Pages 部署结果 |
| Publisher 状态查询 | 核对归档摘要与线上渲染正文 | published、online_verified=true |
| Gmail 工具 | 独立 BCC 发送 HTML、查询发送结果 | 真实 message_id 和持久化去重记录 |

GitHub App 仅配置 Actions read/write、Contents read-only，并只安装到目标仓库。仓库写权限放在 Archive Action 的 `contents: write`，由 `GITHUB_TOKEN` 完成提交；Prompt、HTML 和仓库不包含 PAT 或私钥。私钥保存在部署平台的运行时秘密配置中。

Archive Action 提交后显式调用可复用的 Pages workflow，并传入归档 revision。本实现不只等待机器人提交引发另一条 push workflow，从而让归档与部署属于同一次可追踪发布。

### 2. 连接 MCP，确认实际 schema

本项目的远程地址为：

```text
https://wiki-hub-publisher-production.up.railway.app/mcp
```

Wiki Hub Publisher 是提供工具的 MCP 服务，可以通过插件连接到 ChatGPT。Auth0 负责登录与授权，不提供周报发布工具列表。按照客户端实际连接信息配置回调与注册方式，核对 API audience 与完整 `/mcp` 地址一致，并授权 `reports:publish`。

对于上述 Auth0 错误，分别检查实际客户端是否获准访问该 API，以及用户所在的登录 connection 是否对该客户端启用。DCR 已启用只解决客户端注册入口，不代表这两项授权均已完成。OAuth 元数据、PKCE 及 token 验证流程可参考[OpenAI MCP 鉴权文档](https://developers.openai.com/plugins/build/auth)。

连接后检查任务实际发现的三个工具：

```text
get_publication_by_week(start, end)
get_publication_status(request_id)
publish_weekly_report(
  start, end, html,
  replace_failed_request_id?,
  replace_published_request_id?,
  review_reason?
)
```

按周查询只返回发布状态和历史元数据，不返回完整 HTML。发现 schema 缺少参数时，先确认服务已部署新版本，再根据当前客户端提供的入口重连或重新发现工具；重连后仍须检查实际 schema，不能只凭操作完成就认定刷新成功。

### 3. 把正式内容规则放进仓库 Skill

每次运行读取 `jichuangwei/wiki-hub/main` 的两个完整文件：

- [正式 Skill](https://github.com/jichuangwei/wiki-hub/blob/main/skills/ai-agent-frontend-weekly/SKILL.md)：内容、分类、发布与邮件规则。
- [HTML 模板](https://github.com/jichuangwei/wiki-hub/blob/main/templates/news/ai-agent-frontend-weekly-email.html)：标题与排版的唯一来源。

当前格式是固定五类各 2–4 条，另加独立深度资料 3–5 篇：

1. AI/大模型。
2. Coding Agent/Agent 产品。
3. Agent 开发技术与工程。
4. 前端开发与生态。
5. AI 产业与开发者生态，包含中国生态。
6. AI 编程助手 / Code Agent 深度资料，覆盖中国与国际生态。

按主要事件分类：中国模型发布仍归模型类，Agent 记忆、协议与评测归工程类，不能因为厂商来自中国就统一归产业类。深度栏目可以复用资讯来源，但要增加机制、限制、证据强弱和可执行的前端实验，不能复制资讯段落凑数。

保留模板的 `AI 资讯干货` 主标题、日期、页脚、样式与表格结构；删除未使用图片和占位符。完整 HTML 要保存为可继续访问的产物，同时保存周期、模板 SHA、内容摘要与 request_id。

### 4. 云任务保存短入口 Prompt，运行时读取最新规则

下面是可用于正式每周任务的入口指令。定时设置与私有收件配置需要在任务中实际保存，不能只在文本里声明已设置。

```text
每周一 09:00（Asia/Shanghai）执行上一完整自然周（周一至周日）的
AI × Agent × 前端周报。测试指定周期时使用指定日期，不改变正式定时设置。

开始前读取 jichuangwei/wiki-hub 的 main 分支：
1. skills/ai-agent-frontend-weekly/SKILL.md
2. templates/news/ai-agent-frontend-weekly-email.html
读取完整内容，记录版本与模板 blob SHA，按最新 Skill 和模板执行。
任一读取失败，停止发布和发信并说明原因，不使用旧记忆替代。

生成五类资讯各 2–4 条，并追加独立深度资料 3–5 篇。
核对日期、一手来源、分类、品牌标题和版式，保存完整 UTF-8 HTML。
资料不足或校验失败时，不发布不完整周报。

确认当前任务可调用 get_publication_by_week、publish_weekly_report、
get_publication_status。工具缺失时保留 HTML，报告“发布工具未连接，未触发”。
先查询本周记录和归档：新周才首次发布；已有完整归档默认复用。
同周不同内容必须按 Skill 审核处理；没有用户明确批准，不自动覆盖。
不使用 create_file/update_file，不手动提交，不重跑历史 Action 冒充本次发布。

保存本次 request_id，持续查询同一请求。
只有 state=published、commit_sha 非空、action_conclusion=success、
pages=deployed、online_verified=true，才报告提交并部署成功。
超时或状态不明时保留请求与 HTML，后续继续查询，不盲目创建新请求。

发布核验成功后，按本任务私有邮件配置使用 Gmail 发送完整 HTML。
只使用独立 BCC 字段，To/CC 留空；地址不写入 HTML、仓库或发布参数。
主题为“AI 资讯干货｜START 至 END｜第 N 周”。
正文必须对应本次最终发布的归档，不重新生成另一份邮件正文。
发送前核对 request_id 的持久化去重记录；已成功则跳过。
工具不支持 HTML、BCC 或空 To/CC，或无法可靠去重时，不发送并说明原因。
真实发送成功且保存 message_id 后，才报告邮件已发送。
发送结果不明确时先查询已发送证据，不直接重发。

最后分别报告生成、归档、Action、Pages、线上核验及邮件状态。
给出 request_id、commit SHA、Action/页面链接和真实邮件标识；不公开 BCC 地址。
```

仓库中的[云任务入口](https://github.com/jichuangwei/wiki-hub/blob/main/skills/ai-agent-frontend-weekly/cloud-task-prompt.txt)不存收件人。在云任务私有指令中保留实际 BCC 列表，未来新增地址只改私有配置。仓库文件更新不会自动改写已经保存的定时任务 Prompt 或工具连接。

### 5. 修订历史周报走审核替换

| 旧记录状态 | 处理方式 |
|---|---|
| 无记录且无归档 | 首次调用 publish_weekly_report |
| 已发布、正文一致 | 复用归档与原请求，核对状态 |
| action_failed，未归档 | 用户明确批准后使用 replace_failed_request_id 与 review_reason |
| published，需要新正文 | 用户明确批准后使用 replace_published_request_id 与 review_reason |
| pending、dispatch_unknown 或状态不明 | 查询旧请求，不能替换或盲目再次触发 |

服务核对旧记录、真实归档 commit 与 main 当前摘要；更新已发布内容时，Action 写入前再次检查旧正文摘要。新请求保留替换审计，旧记录不删除。完整新 HTML 必须先保存，否则中断后无法保证用同一版内容继续。

### 6. Gmail 单独验收并防重复

Publisher 的数据库记录发布幂等，不等于已经记录 Gmail 发送。邮件阶段需要另外持久化 `request_id → commit_sha → HTML 摘要 → message_id`，并在并发情况下有互斥机制；无法可靠查询或保存这份记录时，应停止发送。

正式规则要求完整 `text/html; charset=UTF-8` 正文和独立 BCC。实际邮件工具是否支持这些参数必须检查，不假设所有 Gmail 连接器都具备该能力。收件人只来自任务私有配置；任务提醒邮件也不是发给订阅者的周报邮件。

## 验证

### 已验证的发布结果

2026-10-04，第 34–36 周通过 Publisher MCP 审核更新，每期六类数量均为 `2 / 2 / 2 / 2 / 2 / 3`，共 13 个资讯块。查询结果均为 `published`、Action `success`、Pages `deployed`、`online_verified=true`。另核对了归档字节摘要及线上渲染正文，均与生成产物一致。

| 周次与周期 | 归档 commit | Action | 线上页面 |
|---|---|---|---|
| 34：08-17 至 08-23 | [4dba62d](https://github.com/jichuangwei/wiki-hub/commit/4dba62d0e21cc33e6f1284e83d49d6aad0ffb47f) | [37144667415：成功](https://github.com/jichuangwei/wiki-hub/actions/runs/37144667415) | [第 34 周](https://jichuangwei.github.io/wiki-hub/news/2026-week-34/) |
| 35：08-24 至 08-30 | [b1655cb](https://github.com/jichuangwei/wiki-hub/commit/b1655cb16baeee79a9fc6ab11a1fd7cbd82441bb) | [37144795134：成功](https://github.com/jichuangwei/wiki-hub/actions/runs/37144795134) | [第 35 周](https://jichuangwei.github.io/wiki-hub/news/2026-week-35/) |
| 36：08-31 至 09-06 | [ac56550](https://github.com/jichuangwei/wiki-hub/commit/ac56550149b123aec13acea44872b16d808cdfaf) | [37144871064：成功](https://github.com/jichuangwei/wiki-hub/actions/runs/37144871064) | [第 36 周](https://jichuangwei.github.io/wiki-hub/news/2026-week-36/) |

提交信息使用 `docs: archive AI weekly 2026-week-N`。第 35 周本次新请求为 `d0e467d3f71643a88e81745a425537b1`，第 36 周为 `ede91bb6c0e8448394ff5b6b7dbb98f9`，可用于继续查询对应证据。

### 尚需独立完成的验收

在正式 Scheduled Task 自身执行一次 Run now，确认能读取最新 Skill 与模板、发现同一组 MCP 工具，并拿到属于该运行的发布证据。已有聊天发布成功不能代替该项测试；还需观察下一次按计划触发与 OAuth 续期后的运行。

邮件验收需要本次实际 Gmail 发送结果、真实 message_id、BCC 参数证据及持久化发送记录，再复跑相同请求，确认跳过重复发送。第 34–36 周这次修订未发送邮件，所以这里记录的是邮件规则和待验收条件，不声称全链路已经自动发信成功。

维护实现时以[正式 Skill](https://github.com/jichuangwei/wiki-hub/blob/main/skills/ai-agent-frontend-weekly/SKILL.md)、[Publisher 代码](https://github.com/jichuangwei/wiki-hub/blob/main/publisher/server.py)、[Archive workflow](https://github.com/jichuangwei/wiki-hub/blob/main/.github/workflows/archive-report.yml)及[Pages workflow](https://github.com/jichuangwei/wiki-hub/blob/main/.github/workflows/pages.yml)为准；历史文档中单深度栏目的说明不代表当前规则。
