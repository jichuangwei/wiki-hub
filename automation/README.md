# 每周周报归档与发布

模板源为 `templates/reports/ai-agent-frontend-weekly-email.html`。周报正文保持邮件与网站一致，历史归档不覆盖。修改任务要求后运行 `python3 scripts/build_task_prompt.py`；生成 prompt 少于 20,000 字符。

## Actions 发布入口

`.github/workflows/archive-report.yml` 接收 `workflow_dispatch` 输入 `start`、`end`、`html`。日期必须为完整周一至周日；三个输入合计最多 65,535 字符。HTML 当作数据读取，不插入 shell 脚本。入口仅在 main 执行，复用 `archive_report.py`，运行现有测试和完整构建后由 `github-actions[bot]` 提交到 main。只有归档 job 声明 `contents: write`；无 PAT 或额外仓库写凭证。

相同 HTML 重跑不会新增提交；同周不同内容拒绝覆盖。并发归档串行执行，遇到外部并发提交时普通 push 会失败，重新运行前先核实归档，禁止强推。失败不会报告成功。

Actions 的 GITHUB_TOKEN 提交产生的 push 不会启动其他 workflow。因此归档 job 输出真实 commit SHA，deploy job 使用 `workflow_call` 调用现有 `pages.yml` 并检出该 SHA。普通人工提交和手动 Pages 运行仍保留。提交和部署分别报告；部署失败时归档可能已成功，重跑同一 HTML 可重试部署。

已有本地授权的操作员可以触发（身份由现有 GitHub CLI 登录管理，不在命令中填写 token）：

```sh
gh workflow run archive-report.yml --repo jichuangwei/wiki-hub --ref main \
  -f start=2026-09-07 -f end=2026-09-13 -F html=@/path/to/report.html
gh run list --repo jichuangwei/wiki-hub --workflow archive-report.yml
gh run view RUN_ID --repo jichuangwei/wiki-hub
```

也可在 GitHub Actions 页面选择 **Archive weekly report → Run workflow**，填写日期和完整 HTML。不要向输入或正文放入账号、收件人或凭证。部署结果以 deploy job 和实际页面核验为准。

## Scheduled Task 的连接边界

仓库入口不代表 ChatGPT Scheduled Task 已接通。当前聊天的可用 GitHub 工具未提供新运行的 dispatch；Scheduled Task 自身工具和授权须在实际运行中核实，不能从当前聊天直接推断。仅添加 workflow_dispatch 或改写 Prompt 无法补出运行时缺少的工具。

最小可行连接：Scheduled Task 生成并交付完整 HTML，操作员用上述命令或 Actions 页面手动触发一次；仓库写入和 Pages 均由 Actions 完成。当前无需新 token 或中转服务。

无人值守时，先验证 Scheduled Task 可用的输出通道。若任务能发送 Gmail，可由一个外部执行器读取指定周报邮件并调用 dispatch；它使用托管的 GitHub App 安装凭证，仅授予本仓库 Actions write，Contents read，仓库 Contents write 仍只给 Actions。执行器的邮箱读取授权和 GitHub App 私钥放入服务的 secret 存储，不能放 Prompt 或仓库。若运行环境支持已授权 HTTP/MCP 发布工具，同一执行器也可接收该工具请求。当前未配置此执行器，也未修改现有云任务，不声称端到端自动发布成功。

## 本地验证

```sh
python3 scripts/archive_report.py --input /path/to/report.html --start 2026-09-07 --end 2026-09-13
python3 scripts/build_task_prompt.py --check
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
```

2026-10-03 实时检查：仓库公开，Pages 来源为 GitHub Actions，pages.yml 已启用。之前关于私有仓库无法启用 Pages 的记录不再代表当前设置。
