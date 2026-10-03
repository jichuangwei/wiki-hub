每周一 09:00（Asia/Shanghai）执行 AI 编程助手 / Code Agent 深度周报；线上发布核验成功后发送 HTML 邮件，并使用真实 BCC 字段密送。使用上一完整自然周（周一至周日）；测试指定周次时使用指定日期，保持正式任务定时设置不变。

【资料筛选与分析】
先搜索本期资料，最终精选 3–5 篇有实践价值的一手公告、技术文档、论文或工程案例。覆盖中国与国际生态；不足时扩大搜索，仍不足则报告缺口，不凑数或编造。核实事件日期和发布日期，每篇保留可点击 HTTPS 一手来源。每篇包括完整标题、机构与日期、摘要、工程影响，以及两个独立分析段：证据强弱、前端实践。厂商 benchmark 明确标注为厂商评测，机制说明与独立实验证据分开；前端实践给出可执行的实验及判定标准。

【模板和格式】
通过已连接 GitHub 读取 jichuangwei/wiki-hub/main 的 templates/reports/ai-agent-frontend-weekly-email.html，读取完整内容并记录 blob SHA；这是唯一排版源，读取失败则停止发布。复用模板的外壳、栏目行与 story 资讯块，删除旧五栏目示例，改为唯一栏目“01 · AI 编程助手 / Code Agent 深度资料”，添加 3–5 个完整 story 块。在每块中以模板现有段落样式增加“证据强弱：”和“前端实践：”两个 strong 标签段落，保留“摘要：”及“来源：”段落。不要把分析放在 story 块外，不要使用 Markdown 冒充 HTML。无可靠图片则删除整块图片区域。保留结尾：一句话趋势总结、本周动手验证、团队行动建议。删除所有未填占位符，保留完整 UTF-8 HTML。

【标题和版式校验】
深度周报只改变选题与栏目结构，不改变模板的固定品牌标题和版式。主标题 h1 必须逐字保留“AI 资讯干货”，位于日期/周次行上方；HTML title 保留“AI 资讯干货｜日期范围”。页脚品牌保留“AI 资讯干货”。不要把“AI 编程助手 / Code Agent 深度周报”替换进 h1、title 或页脚；深度资料栏目名只写在栏目行。保留模板的标签顺序、class、内联 style、字号、间距、颜色、容器宽度、表格结构和移动端 CSS。只替换占位符、复制 story 块、调整栏目数量、移除未使用图片/产品可选段落，并按现有段落样式增加证据强弱与前端实践。发布前逐项对照完整模板，发现任何未经允许的标题或样式变动则修正后再发布。

【发布】
目标仓库 jichuangwei/wiki-hub，main 分支；归档路径 content/news/reports/ai-agent-frontend/YEAR/ai-agent-frontend-weekly-START-to-END.html，YEAR 取 START 所在年。确认仓库可访问再检查本期归档；默认已有完整归档则复用；只有用户明确要求修订已发布周报时，才按下述审核更新流程重新生成并替换，不把权限错误当成文件不存在。
调用已连接 Wiki Hub weekly publisher 的 publish_weekly_report(start=START, end=END, html=完整HTML)。保存返回的 request_id，再调用 get_publication_status(request_id)。持续查询同一请求，不依赖历史 Action 的最新运行，不重跑旧运行冒充本期发布。请求返回 dispatch_unknown 时，只查询该 request_id，不重复创建发布请求；如仍找不到匹配运行，报告需要检查服务。
仅当 get_publication_status 返回 state=published、commit_sha 非空、action_conclusion=success、online_verified=true，才报告“提交并部署成功”。dispatched 仅表示已触发；deployed_unverified 表示部署成功但线上内容尚未核实；归档成功与部署失败分别说明。相同内容重试复用同一请求，同周不同内容停止并报告需人工审核修正。
不要调用 create_file/update_file，不直接提交文件，不把 PAT/token 或登录凭据写进 Prompt、HTML 或仓库；收件邮箱只允许存在于下方 Prompt 邮件发送配置中，不得写入生成 HTML、publish_weekly_report 的任何参数或仓库归档 HTML。文件写入仅由 Action 的 GITHUB_TOKEN 完成。
如果当前任务没有 publish_weekly_report/get_publication_status 工具，保留完整 HTML 并明确报告“发布工具未连接，未触发”，不得声称已提交或部署，也不得要求每周手动触发来代替自动链路。

【失败请求的审核恢复】
同周不同 HTML 默认停止，不自动覆盖。仅当用户明确批准替换失败且未归档的请求，并提供已审核的新 HTML 时，可调用同一个 publish_weekly_report(start=START, end=END, html=完整HTML, replace_failed_request_id=旧请求ID, review_reason=用户批准及修正原因)。服务会核实旧 Action 已结束且失败、没有归档 commit、main 没有该周归档；满足全部条件才创建新 request_id，保留旧请求证据。不得用于已归档、已成功、运行中或触发状态不明的请求。保存并查询新 request_id，旧请求 state=superseded 时按 replacement_request_id 查询；超时或同参数重试不重复创建请求。邮件去重以最终新请求及归档正文为准，恢复发布不表示邮件已发送。

【HTML 邮件与 BCC】
邮件发送配置：服务固定为 Gmail；收件方式仅 BCC；当前测试 bcc 固定为 2323176669@qq.com；To 和 CC 留空。测试邮箱仅保存在本段配置中，不得复制到 HTML、publish_weekly_report 参数、归档 HTML、邮件主题或公开结果报告。
只有本次 get_publication_status(request_id) 同时返回 state=published、commit_sha 非空、action_conclusion=success、online_verified=true 后，才允许发送邮件；发布失败、发布未完成或线上未核验时不发送。
使用已连接且获授权的 Gmail 发送工具，必须将配置中的测试地址作为独立 bcc 参数传入，不得放入 To、CC、主题或正文。邮件主题为“AI 资讯干货｜START 至 END｜第 N 周”；正文必须为本次生成、最终发布且线上核验通过的完整 UTF-8 HTML，以 text/html; charset=UTF-8 发送。发送前核对日期范围及正文与本次 request_id 对应 commit_sha 的归档 HTML 和线上核验内容一致；复用归档时使用该请求最终发布并核验通过的归档 HTML，不重新生成另一版。不得改成纯文本、Markdown、摘要或只有网页链接。
发送前确认 Gmail 工具实际支持完整 HTML 正文、独立 BCC 参数及 To/CC 留空。工具未连接、未获授权、必需能力缺失或正文无法确认一致时，保留完整 HTML，报告“部署成功，Gmail/BCC 邮件未发送”及原因，不绕过 BCC、不猜测收件人或切换其他服务。
以 request_id 为防重复发送键：同一 request_id 成功后只发送一次。发送前读取持久化发送记录或 Gmail 已发送邮件证据，记录 request_id、commit_sha、HTML 内容摘要及真实 message_id 的对应关系；该记录不得写入周报 HTML 或发布参数。已确认发送成功则复用记录并报告“已发送，跳过重复发送”。并发执行须使用同一 request_id 的互斥发送记录；无法可靠查询或保存记录时不发送，并报告无法保证防重复。
发送超时或结果不明确时先查询同一请求对应的已发送邮件记录；无法确认时报告“发送状态待核实”，不得直接重发。只有 Gmail 返回真实发送成功结果和 message_id（或等效邮件标识），并保存对应发送记录后，才报告“Gmail 邮件已发送（BCC）”；若发送成功但记录保存失败，报告实际发送证据并停止自动重发。草稿创建、生成成功或部署成功均不能当作邮件发送成功。不自动发送历史所有周报，只发送本次指定周期。

【结果】
报告日期、资料条数、模板 blob SHA、归档路径、request_id、真实归档 commit SHA、Action 链接及状态、Pages 状态、线上核验结果及链接。另外单独报告 Gmail/BCC 发送状态（已发送、已发送并跳过重复、未发送或待核实）、原因、对应 request_id、真实 message_id（或等效标识）及 BCC 参数是否已设置，不显示密送地址或任何凭据。运行未完成时保留 request_id，供继续查询；不得把本地生成、归档前校验或任务通知当作部署成功。

【已发布周报的审核更新】
仅当用户明确批准重新生成并更新已 published 的指定周报时，调用 publish_weekly_report(start=START, end=END, html=完整HTML, replace_published_request_id=该周旧请求ID, review_reason=用户批准及修订原因)。不要使用 update_existing 通用开关，不与 replace_failed_request_id 同时传入。发布前保存完整 HTML 文件，不能只保留长度和校验摘要。服务核对旧请求 state=published、真实 commit 与 main 当前归档摘要一致；Action 在写入前复核旧 commit 的正文摘要与当前文件，任何不一致都停止。修订创建新 request_id，旧记录保留为 superseded 审计证据；持续查询新请求，只有新正文 online_verified=true 才算更新成功。新版工具 schema 未包含 replace_published_request_id 时明确报告需要刷新连接元数据，不调用普通发布冒充修订。邮件仍按正式规则及实际发送授权处理，修订部署成功不表示邮件已发送。
