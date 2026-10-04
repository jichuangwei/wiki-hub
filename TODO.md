# 待办

## Publisher 与 CID 邮件上线

记录日期：2026-10-04。配图本地化与 CID 打包代码已完成并验证，现按要求暂存，不纳入当前提交。远程部署及实际邮件发送尚未验证。

Stash 名称：`defer news image archive and CID email pipeline`；创建时为 `stash@{0}`，提交标识 `990860961059b0ea6e24dd2d9a2ee2a6f8419434`。包括下载的图片和邮件产物；本 TODO 保留在工作区。恢复前按名称或提交标识核对，stash 序号可能变化。

- [ ] 准备上线时恢复上述 stash，检查与届时仓库的冲突，重新运行测试与构建。

- [ ] 提交并推送图片归档、网站构建、邮件打包及 Publisher 核验改动。
- [ ] 在 Railway 原 Publisher 服务部署上述提交；确认实际部署的 commit。保留现有环境变量、域名、单实例与 `/data` 持久卷，不重建或清空发布数据库。本次没有新增环境变量或数据库迁移。
- [ ] 检查 `/health` 返回 200，再通过真实带图周报的 `request_id` 核验 `state=published`、`online_verified=true`；仅健康检查通过不能证明发布核验成功。
- [ ] 确认新版归档 Action 将图片与周报一起提交，并生成 `weekly-email-<request_id>` artifact（`report.eml`、`report.gmail.json`）。已有历史运行不会自动补生邮件包。
- [ ] 核实云任务可获取本次 Action 的邮件包，Gmail 工具可接收 MIME 树、CID 内嵌附件及独立 BCC；按新版仓库 skill 执行，私有收件配置保留在云任务中。
- [ ] 按实际发送授权试发，验证常用邮箱中的图片显示及防重复发送记录；发布成功不代表已发信。

### 当前状态与后续上线影响

当前影响流程的修改已全部 stash，工作区使用原有配图与邮件流程，不会因这次修改新增 Publisher 核验不兼容。以下影响仅在恢复并上线该批改动后适用。

仅本地提交不会改变线上。推送并完成 Pages 部署后，网站仍可正常展示本地配图，归档 Action 也可生成邮件包；但旧 Publisher 按原始外链比较 HTML，与新页面的本地图片路径不同，带图周报会停留在 `deployed_unverified`。云任务只有核验为 `published` 才发送邮件，因此自动邮件会被阻止。无图周报不受图片路径差异影响，但其他模板或渲染改动仍需与远程 Publisher 保持一致。

如 Railway 已配置 GitHub 自动部署，推送到其监听分支可能同时更新 Publisher，需查看服务实际部署状态。

部署操作见 [publisher/RAILWAY.md](publisher/RAILWAY.md)；恢复 stash 后，配图与邮件使用见 [README.md](README.md)。
