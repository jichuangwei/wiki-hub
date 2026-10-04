# Wiki Hub 内容维护

本站从仓库内容生成静态页面。编辑 `content/` 中的源文件，不直接修改 `dist/`；`dist/` 是 `scripts/build_site.py` 的生成结果。根路径进入 `/news/`，踩坑记录列表位于 `/notes/`，通用实践经验位于 `/practices/`。

## 新增资讯干货

按内容类型选择一种入口：

1. **每周周报**：以 `templates/news/ai-agent-frontend-weekly-email.html` 为邮件 HTML 模板；AI × Agent × 前端周报按 `skills/ai-agent-frontend-weekly/SKILL.md` 执行。填好完整内容后保存为独立 HTML。用 `python3 scripts/archive_report.py --input /path/to/report.html --start YYYY-MM-DD --end YYYY-MM-DD` 校验并归档。起止日期必须覆盖完整的周一至周日。默认归档到 `content/news/reports/ai-agent-frontend/YEAR/week-N.html`；`YEAR` 与 `N` 取起始日期的 ISO 周年份和周序号。新 AI 周报须保持既定五个栏目，每栏 2–4 条；深入分析融入重点资讯。旧单深度或六栏目归档仅作历史兼容。每条资讯保留摘要和可点击的 HTTPS 一手来源，不能留模板占位符。已有归档不可直接覆盖；同周修订需要单独核对。
2. **独立资讯**：新增 `content/news/items/YEAR/slug.json`。字段格式见 `content/news/items/README.md`。`date` 为实际发布日期，`category`、`title`、至少一个摘要段落和 HTTPS 来源为必填；配图可省略。`YEAR` 必须与 `date` 年份一致，`slug` 使用小写英文字母、数字和连字符。

两种内容都会进入 `/news/`，按所属周展示。`/news/` 默认展示最新周，每周另有可直接访问的固定路径 `/news/YYYY-week-N/`（使用 ISO 周所属年份与周序号，例如 `/news/2026-week-1/`）。新增前核实事实、日期、来源及图片是否对应事件，不用占位链接或示例内容充数。历史邮件 HTML 是归档源；网站构建时会从中提取资讯，页面样式改动应优先修改 `site/` 和生成脚本。

## 新增踩坑记录

复制 `templates/notes/record.md`，保存为 `content/notes/unique-slug.md`。文件名就是详情页路径 `/notes/unique-slug/`：使用小写英文字母、数字和连字符，并在发布后保持稳定；文章标题可以修改，不必因此改路径。

Markdown 开头必须有 `title`、`date`（`YYYY-MM-DD`）和 `summary` 三个字段，后面写正文。按“现象、原因、解决方法、验证”组织内容，写清可复现的步骤和证据；命令、配置与日志用代码块。构建脚本会按日期倒序生成 `/notes/` 列表，并将 Markdown 渲染为详情 HTML。正文支持常用 Markdown、围栏代码块和表格；不要依赖原生 HTML 或未纳入构建的本地图片文件。

## 新增实践经验

在 `content/practices/unique-slug.md` 中使用相同的 `title`、`date`、`summary` 元数据，详情页位于 `/practices/unique-slug/`。实践经验侧重流程、工具分工、设计取舍与可迁移的经验；具体故障的复现与修复仍放在踩坑记录。两类文章共用 Markdown 渲染与样式。文章迁移分类时，在构建脚本的 `ARTICLE_REDIRECTS` 中保留旧路径跳转，避免已发布链接失效。

## 本地验证与发布

首次使用先执行 `python3 -m venv .venv` 和 `.venv/bin/python -m pip install -r requirements-site.txt`。内容变更后运行：

```sh
.venv/bin/python scripts/build_task_prompt.py --check
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python scripts/build_site.py
```

可用 `python3 -m http.server 8765 --bind 127.0.0.1 --directory dist` 预览 `/news/`、`/notes/`、`/practices/` 和新增详情页。推送到 `main` 后，`.github/workflows/pages.yml` 会重新测试、构建并部署 GitHub Pages；提交或本地构建本身不代表线上已更新。
