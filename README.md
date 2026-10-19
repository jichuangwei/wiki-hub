# Wiki Hub

Wiki Hub 是一个公开的静态知识库。资讯干货按周归档不同领域的内容，支持分类和周次切换，邮件与网站使用同一份周报内容；踩坑记录以 Markdown 编写，展示列表和详情页。

## Google Analytics 4 访问统计

站点支持可选的 GA4 统计。未配置衡量 ID 时不加载统计脚本。配置后覆盖首页、各周资讯、踩坑记录和经验笔记的列表及详情；`/news/` 与旧文章跳转页不加载统计，避免跳转重复计数。`localhost`、`*.localhost`、IPv4 回环地址、IPv6 回环地址以及 `file:` 预览不发送统计。

### 首次配置

1. 打开 [Google Analytics](https://analytics.google.com/)，创建 Wiki Hub 的 GA4 媒体资源，将报告时区设为上海。在“管理 → 数据流”中添加网站 `https://jichuangwei.github.io/wiki-hub/`，复制格式为 `G-XXXXXXXXXX` 的**衡量 ID**（不是数字形式的媒体资源 ID，也不是 `GTM-` 容器 ID）。
2. 在网站数据流开启“增强型衡量”的网页浏览、滚动、出站点击。GA4 会记录页面浏览、首次滚动至约 90% 和外链点击；滚动事件只表示到达该深度，不等于读完文章。分类筛选、自定义滚动比例和代码复制不在本次采集范围。
3. 在 GitHub 仓库 **Settings → Secrets and variables → Actions → Variables** 添加仓库变量 `GA4_MEASUREMENT_ID`，值为真实衡量 ID。该 ID 是公开的客户端标识，无需配置 API Secret。发布流程在构建时读取变量，包含周报归档调用的发布流程。
4. 发布代码并完成 `Publish Wiki Hub` 工作流；如果只修改了变量，需手动运行该工作流。变量变化本身不会触发部署。
5. 打开正式站点，在 GA4“实时”报告确认访问；进入一篇长文章、滚动至底部并点击资讯来源，再核对 `page_view`、`scroll`、`click`。标准报表处理可能需要 24–48 小时。不要只以 HTML 含有脚本作为数据已入库的证据。

建议将“管理 → 数据保留”中的用户及事件数据保留设为 14 个月；这项设置不控制标准聚合报表的保留时间。常用报表为“互动 → 网页和屏幕”“获客 → 流量获取”和“互动 → 事件”，具体导航会随媒体资源的报表配置变化。

### 本地构建与验证

```sh
# 未设置 ID 时构建不会加载统计。
.venv/bin/python scripts/build_site.py

# 使用真实 ID 验证生成结果，localhost 预览仍不会上报。
GA4_MEASUREMENT_ID=G-XXXXXXXXXX .venv/bin/python scripts/build_site.py

# 也可用 --ga4-measurement-id 参数，优先于环境变量。
.venv/bin/python scripts/build_task_prompt.py --check
.venv/bin/python -m unittest discover -s tests -q
```

构建会拒绝无效 ID。测试覆盖启用/关闭统计、各类页面与项目子路径、跳转页排除；安装 Node.js 时还会验证初始化、本地预览排除及重复加载去重。

接入使用 Google tag，默认关闭 Google signals 与广告个性化信号，不设置 User-ID 或自定义身份信息。基础测量仍使用 GA4 默认的数据与 Cookie 机制；广告信号关闭不代表无 Cookie。[Google tag 配置](https://developers.google.com/tag-platform/gtagjs/configure)、[增强型衡量](https://support.google.com/analytics/answer/9216061?hl=zh-Hans)、[隐私参数](https://developers.google.com/tag-platform/security/guides/privacy)。

启用统计时，内容页底部显示“访问统计与隐私”，说明数据用途、Cookie 和 Google 的数据处理方式，并提供停用工具及维护者联系入口。

移除仓库变量后重新部署即可关闭采集；历史数据继续由 GA4 后台管理。
