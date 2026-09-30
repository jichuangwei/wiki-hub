# Wiki Hub

公开知识库的静态网站草稿。当前收录 AI、大模型、Coding Agent、Agent 工程及前端生态周报；计划支持跨行业资讯、学习记录和经验文档。首页展示最近 36 条资讯和完整周报归档；每条资讯有独立阅读页，并保留原始来源链接。

## 内容结构

```text
template/weekly-email.html               周报邮件模板原文件
content/reports/YYYY/YYYY-MM-DD-to-YYYY-MM-DD.html
                                         每期完整周报 HTML，唯一内容源
web/                                     网站页面模板、CSS 与交互脚本
scripts/build.py                         从周报生成首页、资讯页和归档页
dist/                                    本地构建结果，不提交
```

周报源文件保持邮件版 HTML。构建脚本解析其中的栏目、资讯、摘要、影响和来源，生成网站页面；归档中的周报页面只增加返回首页的导航与每条资讯的锚点。邮件版模板单独保留，供云端任务通过 GitHub Raw URL 读取。

## 本地预览

需要 Python 3.9 或更高版本，无需安装依赖。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 -d dist
```

打开 `http://localhost:8000/`。在 `dist/news/` 可以查看独立资讯页，在 `dist/reports/` 可以查看完整周报。

## 每周更新

1. 云端任务读取公开模板的原始内容：`https://raw.githubusercontent.com/jichuangwei/wiki-hub/main/template/weekly-email.html`。
2. 完成事实、日期、来源链接和图片校验，生成可发送的完整周报 HTML。
3. 将该 HTML 作为一个新文件提交到 `content/reports/YYYY/YYYY-MM-DD-to-YYYY-MM-DD.html`。日期范围必须是完整的周一至周日。不要覆盖已有期数。
4. `main` 分支收到提交后，GitHub Actions 自动校验、生成资讯页与归档首页，并发布 GitHub Pages。云端任务在确认发布成功后，再把 Pages 链接写入本期邮件或结果摘要。

新增一份周报时，无需手工修改网站首页。构建程序从周报内容生成资讯卡片、独立阅读页、周报归档入口和栏目数量。

### 周报源文件要求

- 使用仓库中的邮件模板，完整保留五个栏目及原始来源链接。
- 文件名与真实日期一致：`YYYY-MM-DD-to-YYYY-MM-DD.html`，目录使用周一所在年份。
- 填完所有 `{{...}}` 占位符。每条资讯包含标题、摘要和至少一个 HTTPS 来源链接。
- 网站保留报告中的外部配图 URL；发布前应检查这些图片可公开访问。

## GitHub Pages

仓库使用 `.github/workflows/pages.yml` 发布 `dist/`。首次部署时，在仓库 **Settings → Pages** 中选择 **GitHub Actions** 作为发布源。站点地址为：

`https://jichuangwei.github.io/wiki-hub/`

发布后，仓库与 Pages 页面均为公开内容。邮件收件人、发送凭证和云任务配置不应提交到这里。
