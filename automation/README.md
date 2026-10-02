# 每周周报任务

将 `weekly-report-prompt.txt` 的完整内容替换到现有云任务中，保留其时间和频率。prompt 通过 GitHub 连接器读取仓库中的完整邮件模板，不依赖本机文件；每次新增当周完整 HTML，网站构建从历史归档提取资讯，默认最新周，分类筛选按周生效。

模板源为 `templates/reports/ai-agent-frontend-weekly-email.html`。模板修改并推送后，云任务下一次会读取新版；修改任务要求后运行 `python3 scripts/build_task_prompt.py`，生成文件必须少于 20,000 字符。网站直接展示完整邮件正文，仅在上方增加分类和周次筛选；正文布局、图片、分析、来源和结尾建议与邮件一致。

云任务需连接 Gmail 和 GitHub，GitHub 连接必须能访问私有仓库 `jichuangwei/wiki-hub` 并新增文件。邮件 To 为发件人自己，BCC 沿用任务 prompt 中的已授权名单。重跑先查询当周归档与已发送邮件，分别跳过已完成步骤；失败时保留 HTML 并报告需要补做的步骤。

本地导入同一份邮件 HTML：

```sh
python3 scripts/archive_report.py --input /path/to/report.html --start 2026-09-21 --end 2026-09-27
python3 scripts/build_site.py
```

相同 HTML 重复导入无副作用；同一周内容不同则拒绝覆盖。历史归档保留，新增 HTML 不需要改周次列表。新文件进入 main 后触发 `.github/workflows/pages.yml` 的检查、构建与部署；部署前仓库必须启用 Pages 的 GitHub Actions 来源。

最近一次核实的接通状态（2026-10-02）：本地 CLI 可访问私有仓库；云 GitHub 连接器读取 README 返回 404；现有云任务尚未定位。GitHub API 明确返回当前计划不支持为该私有仓库启用 Pages，因此发布工作流保持手动禁用。仓库侧实现完成不表示连接权限、云任务或网站发布已配置成功。维持私有仓库时，需要改用支持私有站点的托管服务；改为公开仓库后才可继续使用 GitHub Pages。
