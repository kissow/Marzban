# Marzban 开源扩展功能

本仓库由 Mr.shaw 基于 [Gozargah/Marzban](https://github.com/Gozargah/Marzban) 开发，供其他使用者按开源许可证使用。感谢原作者和贡献者；保留原有 Git 历史与 AGPL-3.0 许可证。本说明只记录本 Fork 的扩展，不把这些功能描述为上游官方功能。

开发参考原项目 `CONTRIBUTING.md`：后端继续使用 FastAPI、SQLAlchemy 和 Alembic，前端沿用 React/Chakra UI。当前配对发布分支为 `feature/mrshaw-release`；合并后由 `kissow/Marzban` 的 `master` 作为唯一日常安装、升级和镜像发布源。原作者仓库只保留为历史基线、许可证及致谢来源，普通安装和升级流程不会自动读取其可执行内容。

## 前端主题兼容约束

- 完整保留官方 Marzban 的 Chakra UI 主题配置、颜色 token、字体、深浅色模式和响应式断点；不修改 `app/dashboard/chakra.config.ts` 来为扩展功能另建视觉系统。
- 新增功能只能组合官方 Chakra 组件和项目已有的表单、按钮、提示、Accordion、间距及状态样式，并放入原有 Node 设置流程；不得使用独立 CSS、硬编码品牌色、独立字体或另一套卡片/布局规范。
- 原版节点名称、启用开关、节点地址、节点端口、API 端口、使用系数、证书查看/下载、保存、删除和重连交互必须继续保留。扩展的健康信息和出站配置只是原节点表单中的附加区块。
- `mrshaw-v0.8.4-preview.3` 将节点弹窗最大宽度调整为 860px、指标区域最大宽度调整为 700px；手机端继续使用原视口断点。仅布局变化，不要求更新 Node。
- `mrshaw-v0.8.4-preview.4`（已发布）将节点弹窗最大宽度调整为 800px，刷新按钮移至运行指标标题旁边，五项指标铺满可用内容区，不额外保留右侧空白；原主题、左右内边距、手机端断点和原功能不变。Actions `36726339140` 已发布 `ghcr.io/kissow/marzban:latest`。

## 当前扩展

- `/api/node/{node_id}/health` 经现有 Node 认证通道读取对应节点的 CPU、内存、磁盘和运行时间；过期或无效快照不显示为实时值。
- 节点管理界面展示上述指标。没有可靠的节点级在线用户来源时，`active_users` 为 `null`，不得把主面板总在线数或服务器 TCP 连接数冒充该值。
- `/api/node/{node_id}/egress` 按节点 ID 保存唯一一条 HTTP/SOCKS 出站配置；新增更多 Node 时各自独立配置住宅 IP。凭据加密存储，API 不回显密码；下发时只给该节点的配置副本添加 `marzban_node_extensions` 扩展，不修改主面板 Xray 配置。
- 配置前先通过 Node 健康响应确认 `managed-outbounds-v1` 能力；不支持的旧 Node 不接收新配置。删除出站会触发节点重启以恢复原路由。
- 用户设置新增设备限制字段：`device_limit`、`device_limit_mode`、`device_limit_action`；普通订阅和指定客户端格式订阅可通过 `X-HWID`、`X-Device-OS`、`X-Device-Model` 登记设备，并由 `/device-status` 返回脱敏统计。原始 HWID 只保存 SHA-256 哈希；`reject_new` 超限返回 `429`，`log_only` 只记录不拒绝。
- 设备限制只属于主面板的订阅请求登记，不修改 Marzban-Node、Xray、证书、端口或已导入配置的连接；不带 `X-HWID` 的旧客户端保持兼容，也不承诺所有客户端都会发送该请求头。

设备限制代码已完成并通过本地专项测试（5 passed）及完整 pytest（22 passed）；SQLite 迁移升级/回滚也已通过。当前仍处于测试中，必须继续完成 PostgreSQL 迁移、并发、Linux 隔离环境和真实客户端验收，才可进入正式发布。它不是 Xray 实时连接数限制。

住宅出口功能必须与同一开发系列的 `kissow/Marzban-node` 配对。HTTP 代理只承载 TCP，UDP 保持原路由。尚未实现住宅代理自动健康检查、故障摘除、按用户/分组路由或真实节点级活跃用户统计。请先在隔离测试节点验证，不要直接替换生产面板和数据库。

节点指标只由 Marzban 向 Node 通过现有认证通道读取，并由 Marzban 的受保护 API 提供。任何获授权的外部项目均可独立调用该 API；本仓库不包含特定业务系统的对接、别名映射或页面代码。

接口用途、`.env` 配置与 API 的区别，以及每次改动必须同步维护文档的发布流程，见 [Mr.shaw 扩展接口与更新规范](MR_SHAW_API_AND_RELEASE.md)。

## Xray 核心版本与功能边界

仓库正式构建基线统一为 `v26.3.27`（稳定版）。主面板和 `Marzban-node` 的 Dockerfile、GitHub Actions 以及安装脚本都通过 `XRAY_CORE_VERSION` 固定到同一版本；不再使用会随时间漂移的 `latest` 核心。`v25.3.6` 和 `1.8.24` 只属于历史 UI 预览示例，不是可安装核心版本。

`v26.9.9` 当前是 Xray-core 的预发布版本，发布说明没有独立的稳定变更清单并指向后续预发布版本。因此它不能直接替换正式镜像的 `latest`，也不能因为核心版本号变大就直接在面板增加一批开关。核心支持某项协议，只表示 Xray 能解析该配置；要成为面板功能，必须同时具备：Marzban 配置模型、配置生成/订阅转换、Node 下发与重启预检、前端表单、客户端兼容性测试和回滚说明。

当前正式版只开放已在本仓库端到端验证过的功能：原有官方入站/订阅能力、REALITY/TLS/WS/gRPC/TCP 等现有配置，以及每个 Node 独立的住宅代理出站。Hysteria 2、Finalmask、XHTTP/3、ECH、WireGuard 等核心能力暂不自动显示为新面板选项；它们需要单独完成配置模型、订阅格式、Node 兼容和客户端测试后，才进入测试版，再决定是否纳入正式版。

如需验证 `v26.9.9`，只能生成独立测试标签（例如 `xray-26.9.9-test`），不覆盖 `latest`，并记录主面板、Node、Xray 配置预检、订阅客户端、回滚和数据卷检查结果。服务器上的 `core-update` 会修改外部 Xray 二进制，可能覆盖容器内版本；生产环境以仓库镜像固定版本为准，禁止把一次手动 `core-update` 当成仓库版本。
## 本地验证

主面板 Python 单元测试：`python -B -m unittest discover -s tests -v`。管理端执行 `tsc --noEmit` 和 `vite build`。Alembic 迁移需在备份后的测试数据库先升级、回滚，再验证原有节点与用户数据。Node 端还需用其配套测试和 Xray 二进制预检。
