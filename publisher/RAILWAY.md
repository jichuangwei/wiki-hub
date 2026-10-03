# Railway + Auth0 部署步骤

## Railway

1. 登录 Railway，新建项目，选择 Deploy from GitHub repo → jichuangwei/wiki-hub，分支 main。项目需要具备常驻容器和持久卷额度；是否产生费用以平台实际账户与配置为准。
2. Root Directory 保留仓库根目录；设置服务变量 RAILWAY_DOCKERFILE_PATH=publisher/Dockerfile，在服务设置选择单实例和 /health 健康检查（300 秒）。不要将 Root Directory 改为 publisher。不要启用 PR 预览复制生产密钥，也不要增加副本。Railway 当前文档已弃用 railway.json/railway.toml，新服务不能依赖该旧配置入口；本次使用控制台设置，后续批量管理可迁移到官方 IaC。
3. 添加持久卷，挂载 /data；设置 PUBLISHER_DB=/data/publications.sqlite3。Railway 卷由 root 挂载，按其官方说明设置 RAILWAY_RUN_UID=0，否则 Dockerfile 中 UID 10001 可能无法写卷。不能只依赖构建时的 chown。卷必须在服务启动时挂载，不能用 pre-deploy 步骤初始化卷。
4. Networking 生成公开 HTTPS 域名。设置 PUBLISHER_URL=https://实际域名/mcp。服务遵守 Railway 提供的 PORT；公开域名的 target port 应对应实际 PORT。/health 无需 OAuth，/mcp 仍受 OAuth 保护。
5. 配置下面的 GitHub App 与 Auth0 变量后 Apply/Deploy。缺少配置时服务会启动失败；看到平台域名不等于部署成功。

## GitHub App

在 GitHub 个人设置的 Developer settings 创建 GitHub App，仅安装到 wiki-hub。权限 Actions read/write、Contents read-only；本桥接不需要 GitHub OAuth 用户登录，也不需要 webhook。

将非秘密的 App ID 和 Installation ID 配置为 GITHUB_APP_ID、GITHUB_INSTALLATION_ID。

私钥有两种配置方式：若平台支持只读 secret 文件，设置 GITHUB_APP_PRIVATE_KEY_FILE 指向可读文件；否则将私钥在自己的电脑上编码为 Base64，在 Railway Variables 设置 GITHUB_APP_PRIVATE_KEY_BASE64 并执行 Seal。只设置一种，不要同时设置 FILE 与 BASE64。Base64 是编码，不是加密；保密依赖平台的 sealed secret。代码只在运行时读取并解码到内存，不写入构建镜像、持久卷、Prompt 或日志。不得在聊天中发送真实值，不提交 .env 或 PEM 文件。

Railway 封存变量会提供给运行环境，且官方也说明会提供给构建环境；本 Dockerfile 不读取构建期 secret，不添加包含私钥的 ARG/ENV/RUN。

## Auth0

1. 创建/使用 Auth0 tenant，创建 Custom API：Identifier 必须与 PUBLISHER_URL 完全一致（包含 /mcp），签名算法 RS256，增加 reports:publish permission。
2. 配置 OAUTH_ISSUER 为 tenant 的实际 issuer（通常末尾带 /），OAUTH_JWKS_URL 为其实际 JWKS URL；OAUTH_ALLOWED_SUBJECTS 填允许发布的个人用户 sub，不能填邮箱或任意用户通配符。
3. 完成授权代码 + PKCE(S256)，并选择 Auth0 当前 tenant 支持的 ChatGPT 客户端身份方式：CIMD、DCR 或预定义客户端。从 ChatGPT 的实际连接页面取得客户端 metadata URL 和回调地址，不固定猜测这些值。不是只创建 API、能签 JWT 就算完成连接。
4. 检查 Auth0 是否启用 Resource Parameter Compatibility Profile，让 MCP 的 resource 参数映射到 API audience；未启用时可能拿到 userinfo audience 或不透明 token，当前服务会拒绝。按 Auth0 tenant 实际界面和官方说明操作；同时核实第三方客户端是否获准访问本 API 与 reports:publish。
5. 在 ChatGPT 完成 OAuth 登录同意，服务需要收到具有正确 iss、aud、exp、sub、scope 的 access token。Scheduled Task 长期运行还需验证授权可续期；不要用短期测试 token 代替真正 OAuth 连接。

## 验收顺序

- GET /health 返回 200：仅进程就绪。
- GET /.well-known/oauth-protected-resource/mcp：核实 resource 为实际 PUBLISHER_URL、authorization_servers 为实际 Auth0 issuer。
- 未登录访问 /mcp 被拒绝；保护元数据必须可读。
- ChatGPT 普通云聊天添加 MCP 地址并完成 OAuth，确认 publish_weekly_report、get_publication_status 可调用。
- 使用云任务实际第 36 周 HTML 发布；通过 request_id 查询直到 state=published，取得真实 commit SHA、Action 链接、Pages 和完整线上正文核验。不能使用测试夹具做正式归档。
- 最后才连接原有每周一 09:00 Scheduled Task，使用仓库 skills/ai-agent-frontend-weekly/cloud-task-prompt.txt，并执行 Run now。普通聊天成功不能证明定时环境拥有同样的连接、写操作授权或 token 续期能力。

当前会话未配置 Railway/Auth0 登录连接；代码已准备不等于远程服务已启动。不要向我发送私钥、PAT 或 Auth0 secret；在对应平台管理界面配置。

参考：[Railway 配置](https://docs.railway.com/config-as-code/reference)、[持久卷权限](https://docs.railway.com/volumes)、[封存变量](https://docs.railway.com/variables)、[健康检查](https://docs.railway.com/deployments/healthchecks)、[Auth0 MCP](https://auth0.com/blog/auth0-auth-for-mcp-servers-generally-available/)、[Auth0 audience 排错](https://support.auth0.com/center/s/article/mcp-audience-error-with-auth0)、[ChatGPT OAuth](https://developers.openai.com/plugins/build/auth)。
