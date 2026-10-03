每周一 09:00（Asia/Shanghai）执行 AI 编程助手 / Code Agent 深度周报，不发送 Gmail。使用上一完整自然周（周一至周日）；测试指定周次时使用指定日期，保持正式任务定时设置不变。

【资料筛选与分析】
先搜索本期资料，最终精选 3–5 篇有实践价值的一手公告、技术文档、论文或工程案例。覆盖中国与国际生态；不足时扩大搜索，仍不足则报告缺口，不凑数或编造。核实事件日期和发布日期，每篇保留可点击 HTTPS 一手来源。每篇包括完整标题、机构与日期、摘要、工程影响，以及两个独立分析段：证据强弱、前端实践。厂商 benchmark 明确标注为厂商评测，机制说明与独立实验证据分开；前端实践给出可执行的实验及判定标准。

【模板和格式】
通过已连接 GitHub 读取 jichuangwei/wiki-hub/main 的 templates/reports/ai-agent-frontend-weekly-email.html，读取完整内容并记录 blob SHA；这是唯一排版源，读取失败则停止发布。复用模板的外壳、栏目行与 story 资讯块，删除旧五栏目示例，改为唯一栏目“01 · AI 编程助手 / Code Agent 深度资料”，添加 3–5 个完整 story 块。在每块中以模板现有段落样式增加“证据强弱：”和“前端实践：”两个 strong 标签段落，保留“摘要：”及“来源：”段落。不要把分析放在 story 块外，不要使用 Markdown 冒充 HTML。无可靠图片则删除整块图片区域。保留结尾：一句话趋势总结、本周动手验证、团队行动建议。删除所有未填占位符，保留完整 UTF-8 HTML。

【标题和版式校验】
深度周报只改变选题与栏目结构，不改变模板的固定品牌标题和版式。主标题 h1 必须逐字保留“AI 资讯干货”，位于日期/周次行上方；HTML title 保留“AI 资讯干货｜日期范围”。页脚品牌保留“AI 资讯干货”。不要把“AI 编程助手 / Code Agent 深度周报”替换进 h1、title 或页脚；深度资料栏目名只写在栏目行。保留模板的标签顺序、class、内联 style、字号、间距、颜色、容器宽度、表格结构和移动端 CSS。只替换占位符、复制 story 块、调整栏目数量、移除未使用图片/产品可选段落，并按现有段落样式增加证据强弱与前端实践。发布前逐项对照完整模板，发现任何未经允许的标题或样式变动则修正后再发布。

【发布】
目标仓库 jichuangwei/wiki-hub，main 分支；归档路径 content/news/reports/ai-agent-frontend/YEAR/ai-agent-frontend-weekly-START-to-END.html，YEAR 取 START 所在年。确认仓库可访问再检查本期归档；已有完整归档则复用，不重新生成或覆盖，不把权限错误当成文件不存在。
调用已连接 Wiki Hub weekly publisher 的 publish_weekly_report(start=START, end=END, html=完整HTML)。保存返回的 request_id，再调用 get_publication_status(request_id)。持续查询同一请求，不依赖历史 Action 的最新运行，不重跑旧运行冒充本期发布。请求返回 dispatch_unknown 时，只查询该 request_id，不重复创建发布请求；如仍找不到匹配运行，报告需要检查服务。
仅当 get_publication_status 返回 state=published、commit_sha 非空、action_conclusion=success、online_verified=true，才报告“提交并部署成功”。dispatched 仅表示已触发；deployed_unverified 表示部署成功但线上内容尚未核实；归档成功与部署失败分别说明。相同内容重试复用同一请求，同周不同内容停止并报告需人工审核修正。
不要调用 create_file/update_file，不直接提交文件，不发送 Gmail，不把 PAT/token、登录凭据或个人收件人写进 Prompt、HTML 或仓库。文件写入仅由 Action 的 GITHUB_TOKEN 完成。
如果当前任务没有 publish_weekly_report/get_publication_status 工具，保留完整 HTML 并明确报告“发布工具未连接，未触发”，不得声称已提交或部署，也不得要求每周手动触发来代替自动链路。

【结果】
报告日期、资料条数、模板 blob SHA、归档路径、request_id、真实归档 commit SHA、Action 链接及状态、Pages 状态、线上核验结果及链接。运行未完成时保留 request_id，供继续查询；不得把本地生成、归档前校验或任务通知当作部署成功。
