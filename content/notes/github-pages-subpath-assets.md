---
title: 示例：GitHub Pages 子路径下静态资源 404
date: 2026-10-03
summary: 页面能打开但样式和脚本失效时，先检查资源路径是否漏掉仓库名。
---

> 这是一篇展示踩坑记录页面结构的示例，不代表 Wiki Hub 线上曾发生此故障。

## 现象

站点部署在 `https://example.github.io/wiki-hub/`。首页能打开，但浏览器开发者工具显示 `wiki-hub.css` 和 `news-filter.js` 返回 404，页面没有样式，筛选也无法使用。

## 原因

GitHub Pages 项目站点的页面位于仓库子路径 `/wiki-hub/` 下。如果页面使用根路径引用资源，浏览器会到域名根目录查找，而不是到仓库目录查找：

```html
<!-- 错误：请求 https://example.github.io/assets/wiki-hub.css -->
<link rel="stylesheet" href="/assets/wiki-hub.css">
```

## 解决方法

从 `/wiki-hub/news/` 页面引用站点公共资源时，使用相对路径：

```html
<link rel="stylesheet" href="../assets/wiki-hub.css">
```

详情页如果位于 `/wiki-hub/notes/example/`，则需要向上返回两级：`../../assets/wiki-hub.css`。构建脚本应按页面深度生成路径，避免手写域名或仓库名。

## 验证

部署后打开开发者工具的 Network 面板，确认 CSS 和脚本请求返回 200；再从列表页进入详情页、返回列表页，检查导航和样式是否正常。
