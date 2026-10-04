---
name: ai-agent-frontend-weekly
description: 筛选国际与中国生态的 AI、大模型、Agent 与前端资讯，生成固定五类周报，按 Wiki Hub 邮件模板归档、核验发布并发送 HTML 邮件；用于每周云任务及同类周报制作。
---

# AI × Agent × 前端周报

默认整理上一完整自然周（周一至周日）的资讯；测试指定周次时使用指定日期。使用固定五栏目模板，线上发布核验成功后，按云任务私有配置发送同一份 HTML 邮件。

## 选题与分类

先广泛搜集候选资讯，再按新颖性、证据质量和开发实践价值筛选。优先采用一手公告、官方文档、论文与工程案例；核实实际事件日期、发布日期、能力描述和 HTTPS 来源。旧资料仅用于解释本周事件，不作为本周新资讯充数。同一事件只归入一个最匹配的栏目，避免同一发布拆成多条或跨栏目重复。

固定五类按模板顺序排列，每类 2–4 条，共 10–20 条：

1. AI/大模型：模型发布、能力、评测、推理成本与限制。
2. Coding Agent/Agent 产品：编程助手与 Agent 产品发布、功能变化、适用场景。
3. Agent 开发技术与工程：SDK、协议、工具调用、运行时、记忆、评测与可靠性工程。
4. 前端开发与生态：框架、浏览器、构建、UI、可访问性、测试与工具链。
5. AI 产业与开发者生态：产业合作、商业模式、开源社区及开发者生态变化；仅有模型或产品功能变化的事件归入对应前列。

整期必须覆盖国际与中国生态，中国资讯按事件归入相应栏目，不集中塞入第五类。资料不足时扩大候选搜索，仍不足则说明具体栏目缺口并保留草稿，停止发布和发信，不用无关内容或重复事件补足数量。

## 内容与分析

每条包含完整标题、日期、1–3 个事件标签、摘要、为什么值得关注或对开发的影响，以及可点击的一手来源。标签可多选，如“模型发布”“产品发布”“开源”“版本更新”“研究进展”，按实际事件填写；沿用模板标签 span，删除未使用占位标签。标签位于来源上方，日期位于资讯标题右侧且保持单行，日期字段只填写日期；发布阶段、修复日期等附加信息写在正文，不单列 SOURCE_NAME；机构信息在正文或来源链接中体现。摘要说明发生了什么；影响说明对谁有用、适用条件与限制。产品资讯额外填写适用场景及理由，非产品资讯删除该可选段落。保留重要事实与限制，减少宣传措辞和空泛评价。

深入分析融入五类中的重点资讯：存在评测争议、复杂机制或明确实践价值时，在该条 story 内按正文样式补充“证据与局限：”或“实践建议：”段落。无需每条都增加分析段，不追加独立深度资料栏目，不重复收录同一事件。厂商 benchmark 标注为厂商评测，官方声明、独立实测与编辑推断分别说明；未实际验证的内容不得写成已验证结果。

本期聚焦用三条核心结论概括本周重点，每条填写加粗短标题与一句说明，沿用模板无序号的聚焦区域。

结尾保留三个部分：一句话趋势总结提炼本周共同变化；本周动手验证给出可执行实验、步骤与判定标准；团队行动建议给出待评估的规则、负责人或流程，每条用加粗短标题加冒号并接同一行说明。实验与团队建议避免重复，不将建议描述成已决策或已落地。

## 模板与发布前检查

通过已连接 GitHub 读取 jichuangwei/wiki-hub/main 的 templates/news/ai-agent-frontend-weekly-email.html 完整内容，并记录 blob SHA。这是唯一排版源，读取失败则停止发布和发信。

保留模板的五个栏目及 01–05 顺序，每类复制 story 块至 2–4 条。主标题 h1 保留“AI 资讯干货”且位于日期上方，HTML title 为“AI 资讯干货｜日期范围”，页脚保留品牌。保留 class、内联 style、字号、间距、颜色、容器宽度、配图布局和移动端 CSS；只填写占位符、复制资讯块、删除可选段落，并按现有正文样式补充重点分析。输出完整 UTF-8 HTML。

每条尽量使用 1–2 张直接对应事件的官方 HTTPS PNG/JPEG/WebP 图片，沿用模板的宽高限制与换行规则。只有一张时清空第二槽位；没有可靠图片时删除整个配图区，不用 Logo 或无关图片凑数。保留准确 alt，不添加图下说明。

发布前核对完整周一至周日的日期、ISO 周年份与周序号、固定五类及条数、事件归类、来源、图片与所有占位符。校验程序对旧单深度或六栏目归档的兼容不代表新报告可以采用这些格式。修订历史周报仅在用户明确授权的范围内执行；复用历史归档时保留原正文。

## 发布

目标仓库 jichuangwei/wiki-hub，main 分支；归档路径 content/news/reports/ai-agent-frontend/YEAR/week-N.html，YEAR 与 N 取 START 的 ISO 周年份和周序号。确认仓库可访问再检查本期归档；默认已有完整归档则复用；只有用户明确要求修订已发布周报时，才按下述审核更新流程重新生成并替换，不把权限错误当成文件不存在。
确认仓库可访问后，先调用 get_publication_by_week(start=START, end=END) 查该周当前 publication 与替换历史，再检查 main 上的归档文件。该工具只返回请求与状态元数据，不返回 HTML。若当前 publication 内容与目标归档一致，复用它并按 request_id 调用 get_publication_status；若该周没有 publication 且归档不存在，才调用 publish_weekly_report(start=START, end=END, html=完整HTML)。若存在不同内容的记录，先用其 request_id 查询状态：dispatch_unknown、pending 或状态不明时停止并继续查原请求；action_failed 且未归档时，只有用户明确批准修正后才可传 replace_failed_request_id 与 review_reason；已 published 时，只有用户明确批准更新后才可传 replace_published_request_id 与 review_reason。没有明确批准就停止并报告需要审核，不得普通重试或覆盖。

发布后保存返回的 request_id，再调用 get_publication_status(request_id)。持续查询同一请求，不依赖历史 Action 的最新运行，不重跑旧运行冒充本期发布。请求返回 dispatch_unknown 时，只查询该 request_id，不重复创建发布请求；如仍找不到匹配运行，报告需要检查服务。
仅当 get_publication_status 返回 state=published、commit_sha 非空、action_conclusion=success、online_verified=true，才报告“提交并部署成功”。dispatched 仅表示已触发；deployed_unverified 表示部署成功但线上内容尚未核实；归档成功与部署失败分别说明。相同内容重试复用同一请求，同周不同内容停止并报告需人工审核修正。
不要调用 create_file/update_file，不直接提交文件，不把 PAT/token 或登录凭据写进 Prompt、HTML 或仓库；收件邮箱只允许存在于云任务私有 Prompt 邮件发送配置中，不得写入生成 HTML、publish_weekly_report 的任何参数或仓库归档 HTML。文件写入仅由 Action 的 GITHUB_TOKEN 完成。
如果当前任务没有 publish_weekly_report、get_publication_status 或 get_publication_by_week 工具，保留完整 HTML 并明确报告“发布工具未连接，未触发”，不得声称已提交或部署，也不得要求每周手动触发来代替自动链路。

## 失败请求的审核恢复

同周不同 HTML 默认停止，不自动覆盖。仅当用户明确批准替换失败且未归档的请求，并提供已审核的新 HTML 时，可调用同一个 publish_weekly_report(start=START, end=END, html=完整HTML, replace_failed_request_id=旧请求ID, review_reason=用户批准及修正原因)。服务会核实旧 Action 已结束且失败、没有归档 commit、main 没有该周归档；满足全部条件才创建新 request_id，保留旧请求证据。不得用于已归档、已成功、运行中或触发状态不明的请求。保存并查询新 request_id，旧请求 state=superseded 时按 replacement_request_id 查询；超时或同参数重试不重复创建请求。邮件去重以最终新请求及归档正文为准，恢复发布不表示邮件已发送。

## HTML 邮件与 BCC

邮件服务与收件人由云任务私有 Prompt 配置，不写入公开仓库。当前流程使用 Gmail，收件方式仅 BCC；To 和 CC 留空。没有明确的私有 BCC 配置时不发送邮件。收件地址不得复制到 HTML、publish_weekly_report 参数、归档 HTML、邮件主题或公开结果报告。
只有本次 get_publication_status(request_id) 同时返回 state=published、commit_sha 非空、action_conclusion=success、online_verified=true 后，才允许发送邮件；发布失败、发布未完成或线上未核验时不发送。
使用已连接且获授权的 Gmail 发送工具，必须将云任务私有配置中的地址作为独立 bcc 参数传入，不得放入 To、CC、主题或正文。邮件主题为“AI 资讯干货｜第 N 周｜START 至 END”；正文必须为本次生成、最终发布且线上核验通过的完整 UTF-8 HTML，以 text/html; charset=UTF-8 发送。发送前核对日期范围及正文与本次 request_id 对应 commit_sha 的归档 HTML 和线上核验内容一致；复用归档时使用该请求最终发布并核验通过的归档 HTML，不重新生成另一版。不得改成纯文本、Markdown、摘要或只有网页链接。
发送前确认 Gmail 工具实际支持完整 HTML 正文、独立 BCC 参数及 To/CC 留空。工具未连接、未获授权、必需能力缺失或正文无法确认一致时，保留完整 HTML，报告“部署成功，Gmail/BCC 邮件未发送”及原因，不绕过 BCC、不猜测收件人或切换其他服务。
以 request_id 为防重复发送键：同一 request_id 成功后只发送一次。发送前读取持久化发送记录或 Gmail 已发送邮件证据，记录 request_id、commit_sha、HTML 内容摘要及真实 message_id 的对应关系；该记录不得写入周报 HTML 或发布参数。已确认发送成功则复用记录并报告“已发送，跳过重复发送”。并发执行须使用同一 request_id 的互斥发送记录；无法可靠查询或保存记录时不发送，并报告无法保证防重复。
发送超时或结果不明确时先查询同一请求对应的已发送邮件记录；无法确认时报告“发送状态待核实”，不得直接重发。只有 Gmail 返回真实发送成功结果和 message_id（或等效邮件标识），并保存对应发送记录后，才报告“Gmail 邮件已发送（BCC）”；若发送成功但记录保存失败，报告实际发送证据并停止自动重发。草稿创建、生成成功或部署成功均不能当作邮件发送成功。不自动发送历史所有周报，只发送本次指定周期。

## 结果

报告日期、资料条数、模板 blob SHA、归档路径、request_id、真实归档 commit SHA、Action 链接及状态、Pages 状态、线上核验结果及链接。另外单独报告 Gmail/BCC 发送状态（已发送、已发送并跳过重复、未发送或待核实）、原因、对应 request_id、真实 message_id（或等效标识）及 BCC 参数是否已设置，不显示密送地址或任何凭据。运行未完成时保留 request_id，供继续查询；不得把本地生成、归档前校验或任务通知当作部署成功。

## 已发布周报的审核更新

仅当用户明确批准重新生成并更新已 published 的指定周报时，调用 publish_weekly_report(start=START, end=END, html=完整HTML, replace_published_request_id=该周旧请求ID, review_reason=用户批准及修订原因)。不要使用 update_existing 通用开关，不与 replace_failed_request_id 同时传入。发布前保存完整 HTML 文件，不能只保留长度和校验摘要。服务核对旧请求 state=published、真实 commit 与 main 当前归档摘要一致；Action 在写入前复核旧 commit 的正文摘要与当前文件，任何不一致都停止。修订创建新 request_id，旧记录保留为 superseded 审计证据；持续查询新请求，只有新正文 online_verified=true 才算更新成功。新版工具 schema 未包含 replace_published_request_id 时明确报告需要刷新连接元数据，不调用普通发布冒充修订。邮件仍按正式规则及实际发送授权处理，修订部署成功不表示邮件已发送。
