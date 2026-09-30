# Marzban 开源扩展功能

本仓库由 Mr.shaw 基于 [Gozargah/Marzban](https://github.com/Gozargah/Marzban) 开发，供其他使用者按开源许可证使用。感谢原作者和贡献者；保留原有 Git 历史与 AGPL-3.0 许可证。本说明只记录本 Fork 的扩展，不把这些功能描述为上游官方功能。

开发参考原项目 `CONTRIBUTING.md`：后端继续使用 FastAPI、SQLAlchemy 和 Alembic，前端沿用 React/Chakra UI。当前配对发布分支为 `feature/mrshaw-release`；合并后由 `kissow/Marzban` 的 `master` 作为唯一日常安装、升级和镜像发布源。原作者仓库只保留为历史基线、许可证及致谢来源，普通安装和升级流程不会自动读取其可执行内容。

## 前端主题兼容约束

- 完整保留官方 Marzban 的 Chakra UI 主题配置、颜色 token、字体、深浅色模式和响应式断点；不修改 `app/dashboard/chakra.config.ts` 来为扩展功能另建视觉系统。
- 新增功能只能组合官方 Chakra 组件和项目已有的表单、按钮、提示、Accordion、间距及状态样式，并放入原有 Node 设置流程；不得使用独立 CSS、硬编码品牌色、独立字体或另一套卡片/布局规范。
- 原版节点名称、启用开关、节点地址、节点端口、API 端口、使用系数、证书查看/下载、保存、删除和重连交互必须继续保留。扩展的健康信息和出站配置只是原节点表单中的附加区块。
- `mrshaw-v0.8.4-preview.3` 将节点弹窗最大宽度调整为 860px、指标区域最大宽度调整为 700px；手机端继续使用原视口断点。仅布局变化，不要求更新 Node。

## 当前扩展

- `/api/node/{node_id}/health` 经现有 Node 认证通道读取对应节点的 CPU、内存、磁盘和运行时间；过期或无效快照不显示为实时值。
- 节点管理界面展示上述指标。没有可靠的节点级在线用户来源时，`active_users` 为 `null`，不得把主面板总在线数或服务器 TCP 连接数冒充该值。
- `/api/node/{node_id}/egress` 按节点 ID 保存唯一一条 HTTP/SOCKS 出站配置；新增更多 Node 时各自独立配置住宅 IP。凭据加密存储，API 不回显密码；下发时只给该节点的配置副本添加 `marzban_node_extensions` 扩展，不修改主面板 Xray 配置。
- 配置前先通过 Node 健康响应确认 `managed-outbounds-v1` 能力；不支持的旧 Node 不接收新配置。删除出站会触发节点重启以恢复原路由。

此功能必须与同一开发系列的 `kissow/Marzban-node` 配对。HTTP 代理只承载 TCP，UDP 保持原路由。尚未实现住宅代理自动健康检查、故障摘除、按用户/分组路由或真实节点级活跃用户统计。请先在隔离测试节点验证，不要直接替换生产面板和数据库。

节点指标只由 Marzban 向 Node 通过现有认证通道读取，并由 Marzban 的受保护 API 提供。任何获授权的外部项目均可独立调用该 API；本仓库不包含特定业务系统的对接、别名映射或页面代码。

接口用途、`.env` 配置与 API 的区别，以及每次改动必须同步维护文档的发布流程，见 [Mr.shaw 扩展接口与更新规范](MR_SHAW_API_AND_RELEASE.md)。

## 本地验证

主面板 Python 单元测试：`python -B -m unittest discover -s tests -v`。管理端执行 `tsc --noEmit` 和 `vite build`。Alembic 迁移需在备份后的测试数据库先升级、回滚，再验证原有节点与用户数据。Node 端还需用其配套测试和 Xray 二进制预检。
