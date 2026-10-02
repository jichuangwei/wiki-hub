# 独立资讯

每条独立资讯保存为 `YYYY/slug.json`，不需要属于任何周报。分类由内容的 `category` 字段决定，可以是任意行业或主题；同名分类会在首页自动合并。示例结构：

```json
{
  "date": "2026-09-30",
  "category": "科技",
  "title": "资讯标题",
  "source_name": "发布机构",
  "sections": [
    {"title": "摘要", "text": "已核实的内容摘要。"},
    {"title": "为什么值得关注", "text": "对读者的具体影响。"}
  ],
  "sources": [
    {"label": "官方公告", "url": "https://example.com/announcement"}
  ],
  "image": {"url": "https://example.com/image.jpg", "alt": "图片说明"}
}
```

`image` 可以省略。日期、标题、分类、摘要和至少一个 HTTPS 来源链接为必填。发布前需核实事实与图片授权；示例 URL 仅说明格式，不是可发布资讯。
