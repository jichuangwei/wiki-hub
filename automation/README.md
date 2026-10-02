# 深度周报定时发布

正式任务：每周一 09:00（Asia/Shanghai），筛选 3–5 篇 AI 编程助手 / Code Agent 深度资料，分析证据强弱及前端实践，生成 HTML，归档并部署 Pages。不发送 Gmail。

## 云端链路

Scheduled Task → `publish_weekly_report(start, end, html)` → `archive-report.yml` → bot 提交 main → 复用 `pages.yml` → `get_publication_status(request_id)` 核实线上内容。

发布工具代码、容器和完整部署/授权配置见 [publisher/README.md](../publisher/README.md)。发布工具需要部署到常驻 HTTPS 服务，安装仅 Actions write、Contents read 的 GitHub App，配置外部 OAuth 授权，并将该远程 MCP 连接提供给云任务。Contents write 仅在 Action 的归档 job 中使用。

`weekly-report-instructions.md` 是完整任务要求；运行 `python3 scripts/build_task_prompt.py` 同步 `weekly-report-prompt.txt`，再更新现有云任务。仓库修改不会自动修改 ChatGPT 云任务的 Prompt、时间或连接。没有发布工具时仅改 Prompt 仍不能自动发布。

## HTML 格式

唯一排版源：`templates/reports/ai-agent-frontend-weekly-email.html`。深度报告复用模板外壳、栏目、story 资讯块，唯一栏目为 `01 · AI 编程助手 / Code Agent 深度资料`。必须有 3–5 篇，每篇保留完整摘要、HTTPS 来源、非空“证据强弱”和“前端实践”分析段；保留三个结尾段。历史五栏目报告继续按每栏 2–4 条校验，不修改历史正文。日期必须是完整周一至周日。

## 工作流与运行证据

`archive-report.yml` 接收 start、end、html 和可选 request_id（32 位小写十六进制）。输入合计最多 65,535 字符，仅在 main 执行。完整 HTML 作为数据读取，不插入 shell。相同周报字节不新增提交，已有不同正文拒绝覆盖；归档并发串行执行，禁止强推。

GITHUB_TOKEN 提交产生的 push 不会启动另一个 workflow，所以归档入口显式调用现有 pages.yml，检出归档 job 输出的真实 revision。普通提交仍走 Pages 的 push 入口。

运行名包含 request_id，成功归档后上传 publication.json 证据（请求、日期、revision、正文 SHA-256，保存 90 天）。发布工具依据本请求对应的运行及证据核对内容，不把启动工作流的 head SHA 当作新归档 commit SHA，不使用最近历史运行冒充本次运行。提交、部署和线上核验分别报告。

## 验证

```sh
python3 scripts/build_task_prompt.py --check
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
uv run --python 3.11 --with-requirements publisher/requirements.lock python -m unittest publisher.test_server -v
```

开发测试使用合成 HTML 夹具；正式第 36 周验收必须用云任务生成的真实完整 HTML。代码测试通过不代表远程服务部署、账号连接或云任务端到端发布成功。
