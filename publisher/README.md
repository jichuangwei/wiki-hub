# Scheduled Task 发布工具

这是远程 MCP 服务，不依赖本机常开，不替代 ChatGPT Scheduled Task 的定时器。仅提供 `publish_weekly_report(start, end, html)` 和 `get_publication_status(request_id)`，目标固定为 `jichuangwei/wiki-hub/main`。发布触发新的 `archive-report.yml`，由 Action 写入仓库并调用 Pages。工具本身没有 Contents write。

## 部署前需要的外部配置

1. 创建并安装 GitHub App，仅选择 wiki-hub；仓库权限 Actions read/write、Contents read-only。无需 PAT。App 私钥使用只读 secret 文件或平台封存变量，不能放 Git 仓库、Docker build context 或 Prompt。App ID、安装 ID 是非秘密配置。
2. 提供支持 OAuth 2.1、PKCE 和 MCP 客户端接入的授权服务器：HTTPS issuer、JWKS、RS256 access token、audience 为本服务完整 MCP URL，scope 为 reports:publish。配置准许的用户 sub；不能允许任意登录用户发布。按客户端要求配置注册和回调；本服务验证外部授权服务器的 token，不包含登录/注册服务器。
3. 部署单实例容器与持久化 `/data`，设置 HTTPS 反向代理，公开 `/mcp` 和 SDK 的 OAuth protected-resource metadata 路由。域名转发 Host 需与 PUBLISHER_URL 一致。设置请求体上限至少 512 KB、外部限流；服务仅支持单副本共享本地 SQLite。不要用临时磁盘丢弃幂等记录，不要从 Docker 构建上下文复制私钥。

服务环境变量（仅名称，真实值在平台配置，私钥不粘贴到聊天）：

| 名称 | 用途 |
|---|---|
| PUBLISHER_URL | 完整 HTTPS MCP URL，如 https://publisher.example.com/mcp |
| OAUTH_ISSUER | 外部 OAuth issuer，必须与 token iss 完全一致 |
| OAUTH_JWKS_URL | 授权服务器的 HTTPS JWKS 地址 |
| OAUTH_ALLOWED_SUBJECTS | 允许发布的用户 sub，逗号分隔 |
| GITHUB_APP_ID | GitHub App ID |
| GITHUB_INSTALLATION_ID | 仅 wiki-hub 的安装 ID |
| GITHUB_APP_PRIVATE_KEY_FILE | 挂载的私钥文件绝对路径，与 BASE64 二选一 |
| GITHUB_APP_PRIVATE_KEY_BASE64 | 运行时读取的 Base64 私钥，仅存放平台封存变量，与 FILE 二选一 |
| PUBLISHER_DB | 持久化 SQLite 路径，容器默认 /data/publications.sqlite3 |

从仓库根目录构建：

```sh
docker build -f publisher/Dockerfile -t wiki-hub-publisher .
```

部署时挂载 /data 可写卷和平台只读私钥 secret；内部端口 8000 只交给 HTTPS 反向代理，不能作为匿名公网入口。Docker 用户 UID 10001，需要有读 secret 文件及写数据卷权限。启动缺少配置时会失败；未授权请求不能调用工具。Python 运行时要求 >=3.10，容器使用 3.12；依赖来自已锁定 requirements.lock。

## 连接云任务

在 ChatGPT 中按账号支持的自定义 MCP/插件连接流程添加 HTTPS MCP 地址，完成 OAuth 登录，在普通云聊天确认两个工具可用，再将该连接提供给正式 Scheduled Task。使用 automation/weekly-report-prompt.txt 更新已有任务；每周一 09:00，Asia/Shanghai，线上核验成功后由云任务已连接的邮件工具发送 HTML 邮件并密送 BCC。Publisher 本身不发送邮件，邮件服务与收件人只配置在云任务私有任务指令中。仓库文件更新不代表云任务 Prompt 或连接已更新。若账号/工作区不允许自定义连接或定时执行写操作，需要先处理管理员/平台限制，不能宣称自动发布已接通。

## 新格式与验收

深度周报使用原 HTML 模板，只保留唯一栏目 `01 · AI 编程助手 / Code Agent 深度资料`，3–5 个完整 story 块，每篇必须包含非空的 `证据强弱`、`前端实践` 分析段；保留摘要、HTTPS 来源和三个结尾段。旧五栏目报告继续采用原校验，不修改历史文件。

云任务传入完整 HTML 后保存 request_id，仅查询该请求。服务按周和 HTML 哈希进行幂等处理，日期或不同正文冲突不覆盖。HTTP 超时后不会自动重发 dispatch；查不到运行时由操作员核对 GitHub 和数据库。Action 失败可由操作员核实后在 GitHub 重跑该运行，查询工具继续追踪同一 run。不要删除数据库记录来盲目重试。

验收必须分层：触发成功不是提交成功；查询工具先校验与 request_id 匹配的运行及 archive artifact，读取真实 revision 上的文件并核对 SHA-256。整个 Action（含 Pages）成功后，再核实线上指定周正文、标题、来源与归档一致，返回 state=published 才算完整成功。Pages 暂时无法访问时返回 deployed_unverified，继续查询。证据 artifact 保留 90 天；过期后不能凭空恢复验证结果，仍可人工查 Git 历史与部署记录。

当前代码交付不等于服务已部署、GitHub App 已安装或云任务连接已完成。第 36 周须使用云任务实际生成的完整 HTML 测试，不能用测试夹具代替正式周报。

Railway 的具体部署步骤见 [RAILWAY.md](RAILWAY.md)。在部署平台指定 Dockerfile、单实例及 /health 检查，运行时遵守平台 PORT；/health 仅证明进程就绪，不证明 GitHub 或 OAuth 已连通。

实现参考：[GitHub dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)、[MCP Python SDK authorization](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/authorization.md)。

## 审核恢复失败且未归档的请求

用户明确批准后，调用 `publish_weekly_report` 并提供 `replace_failed_request_id` 和非空 `review_reason`。仅允许替换已结束且失败、没有归档 commit 且 main 无该周文件的请求；已有归档仍拒绝修改。创建新 request_id 前用 SQLite 事务保留旧记录、旧运行状态、审核原因和新 digest。旧请求返回 `superseded` 及 `replacement_request_id`；同一替代正文重试复用新请求，超时保留 `dispatch_unknown`，不能盲目再次派发。该功能不删除数据库、不放宽 GitHub 权限、不触发邮件。线上核验访问对应的 `/news/YYYY-week-N/` 页面。
