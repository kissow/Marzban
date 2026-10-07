# Marzban 开源扩展功能

## MR-20261008-NODE-RELAY-SOURCES（镜像已发布，服务器/视觉验收待完成）

连接方式采用原React/Chakra独立管理弹窗和原信息图标。可选择Marzban主服务器或另一台源Node中转到目标Node；保留原订阅别名、顺序、数量，只替换精确匹配的端点，不新增Relay。目标认证、设备凭据和出口不变。自转发/环路/占用/能力/精确ACK/失败回滚、来源隔离与恢复有回归测试。

管理API增加source/source_node_id/来源列表，additive迁移9012ab34cd56；Node新增managed-node-relay-v1、原认证REST/RPyC完整快照与独立转发进程。固定Xray26.3.27，原证书、控制/API端口、用户、.env与数据卷保留。首版VLESS TCP/RAW REALITY、IPv4/DNS-only入口、单跳选择，不是所有协议或任意UDP转发；每源512个配置不是吞吐承诺。

本地最终代码和独立发布副本再次复测：主控164/164、Node60/60（准备固定Xray，无跳过）、前端47/47、类型/生产构建、依赖/diff通过。干净Linux CI与两镜像双架构发布核对完成；真实跨服务器mTLS、公网吞吐、多引擎数据库、实际原组件UI截图仍待验收，不标稳定版。UI截图因浏览器策略blocked，未绕过。

主控revision 93bfbb5b17dd8ee731449976df1a4af4e0f57ca5，Actions37657985804；Node revision 7b45fc0dc3b4451045a06123b52ccdaaa5911b8d，Actions37657976968。scripts合并ed274ba82410f9e6f580cbec59b2a15a89ab81ea，Actions37657994843成功，脚本运行时不变。先在承担来源的Node运行marzban-node update，再在主控运行marzban update；仅作目标的既有配对Node不强制更新。新Node沿用仓库install，现在拉取新latest；旧机不重装、不删卷、不重复adopt。源业务入口TCP需放行，客户端刷新订阅。

[精确配对SHA、index/架构/config摘要、接口与SSH验收证据](https://github.com/kissow/Marzban/blob/master/docs/NODE_RELAY_SOURCES_RELEASE.md)。下方旧记录只描述各自日期的阶段，不代替本轮最新状态；文档[skip ci]提交不改变已核对的运行时镜像revision。


## MR-20261007-RELAY-INTERNAL-SUBSCRIPTION（本地修复，未发布）

保留原订阅别名/数量/顺序，匹配 Node 时只换地址与端口，不新增中转条目；关闭恢复直连。原 Hosts、证书、用户凭据和转发进程不改，short ID 按输出副本处理。Node/scripts 无变化；Node→Node 当前未实现。[行为、兼容与验证](docs/NODE_RELAY_SUBSCRIPTION.md)。

## MR-20261007-NODE-RELAY（镜像已发布，服务器待验收）

主服务器可选每 Node TCP 中转，首版仅 VLESS TCP/RAW REALITY、IPv4 入口。原直连条目、用户凭据、REALITY 参数、证书、Node 控制/API/倍率/住宅出口保留；Node/scripts 无本轮运行时或命令变化、不需服务器更新，Xray 固定 v26.3.27。新增四个 sudo API、node_relays additive 迁移 8f9012ab34cd、独立进程及失败恢复；running 仅代表本地监听就绪。

用户已授权先发布。源 134f12faf5e29e53986ff271a8c8f57b8a38db38，PR #16 合入 d23502030358930592016f9ff2f7d3f42acad4e7；PR CI 37637526876 成功（140 项普通后端 + 两项显式真实 Linux Xray、前端44/44、类型/生产构建），本地最终142/142及前端44/44复核通过。正式 Actions 37637973415 首次成功；latest index sha256:252adac60cdcbcc83a7ef13a080d52876876017a65220c58fcf76539db9ccd03 与 amd64/arm64 manifest/config/OCI revision 已核对（d23502030358930592016f9ff2f7d3f42acad4e7）。仅文档回写 [skip ci] 不改变该运行时版本。UI 截图受浏览器管理策略阻止，服务器、公网 REALITY/手机与实际提速仍待验收，不冒称稳定发布。 [设置、接口、限制、回滚与测速](docs/NODE_RELAY.md)。

## MR-20261007-BROWSER-TRANSLATION（镜像已发布，服务器验收待完成）

HTML/body 浏览器翻译保护覆盖 React 根与 Chakra Portal；主机设置的加载/空列表文字由原 Text 组件包裹，避免外部翻译替换文本后卸载崩溃。原主题、宽度、表单、四语言与所有配置保留；无 API/数据库/Node/scripts/Xray 变化。PR #14 / 96599563 合入、正式 Actions 37494615636 成功，latest 双架构摘要/revision 已核对；既有 Fork 主控 marzban update 后重新加载页面，Node 无需更新。服务器和实际翻译服务验收仍待用户执行。[详细记录](docs/BROWSER_TRANSLATION.md)。

## MR-20261006-CONTROL-RESILIENCE（镜像已发布，服务器验收待完成）

修复慢控制链路被当作会话失效的问题：保留 session、只对精确 Session mismatch 重新认证；只读请求有限重试，变更请求不立即重放；不确定健康异常退避而不盲目重启核心。并行健康探测、单快照/互斥批量账号同步及流量/日志异常隔离，防止故障扩散到健康节点。两轮 116/116、专项 20/20 与真实传输 13/13 各连续复跑三轮通过。API/数据/UI/证书/端口/HWID/Xray v26.3.27 不变，Node/scripts 不需本轮更新。[接口期限、边界、证据与验收](docs/NODE_CONTROL_RESILIENCE.md)。

PR #12 合入 `eb43761e`，正式 Actions `37486719383` 成功；GHCR latest index 与 amd64/arm64 OCI revision 已核对。已切换 Fork 的主控执行 `marzban update`；服务器部署与至少 30 分钟真实链路/客户端验收仍待用户执行。仅文档证据回写使用 `[skip ci]`，不改变已验证运行时镜像 revision。

## MR-DASHBOARD-I18N-MOBILE：多语言与手机入站弹窗（镜像已发布，服务器/视觉验收待完成）

在原 React/Chakra 组件内完善四种语言文案、在线/到期时间、日历、状态筛选及原表单校验；保留技术名称与 API 枚举。设置入站桌面 440px，手机最大为视口减 24px，长标题/原帮助/操作行可换行。主题、协议、证书、端口、数据、HWID/UDP、Xray v26.3.27 不变；Node/scripts 无本轮变化或更新要求。

本地/Linux CI 语言回归 34/34、主控回归 95/95、类型和构建通过；PR #11 合入 `56552130`、Actions `37353281396` 成功，latest 双架构 digest/OCI revision 已核对。实际浏览器视觉和服务器验收待完成，不宣称稳定上线。[详情及更新命令](docs/DASHBOARD_I18N_MOBILE.md)。

## MR-20261006-NODE-RECOVERY（镜像已发布，服务器验收待完成）

节点连接/重启/管理修改删除使用每节点生命周期锁；重复重连合并，自动失败恢复退避 30 秒，手动绕过退避。复用失效会话 transport，失败重启不无条件停远程核心；健康故障隔离，恢复时清旧状态。TLS 握手增加阶段超时并保留双向认证，错误写入原 message。全用户账号协调移出节点锁。

同一最终代码两轮 95/95 与 Linux CI、前端/依赖检查通过；UI、API/schema、用户数据、证书、端口、HWID/UDP 和 Xray v26.3.27 不变。Node/scripts 无运行时变化无需本轮更新。PR #10、源 `122632c8` 与 Actions `37340574125` 已完成；latest 双架构摘要和 OCI revision 已核对，服务器验收未执行。[发布证据和边界](docs/NODE_RECOVERY_RELEASE.md)。

## MR-20261003-SCHEDULER-DEPENDENCY：调度器依赖维护（镜像已发布，服务器验收待完成）

APScheduler 已从 `3.9.1.post1` 升级并锁定为 `3.11.3`，移除旧版本导入 `pkg_resources` 产生的弃用警告。调度器仍使用原有 BackgroundScheduler、UTC、interval、coalesce 和 max_instances 配置；不新增菜单、API、数据库字段、Node 通道、证书、端口或 Xray 功能。主控连接修复与本条一起验证，Node 运行时代码本轮无需更新。

本地/Linux CI 69/69 与前端构建通过；源 `78e7b8e`、Actions `37135175798` 成功，双架构 latest 与 OCI revision 已核对。服务器真实网络验收待完成。[发布证据和兼容边界](docs/NODE_CONNECTION_RELEASE.md)。

## MR-20261003-DONATION-LINK：捐赠入口维护

新主面板 latest 已发布：源 e72943b、Actions 37123809995 成功，两个架构的 digest/revision 核对通过；服务器点击验收待完成。Node/scripts 不需更新。

原捐赠菜单保持原结构与主题，只将目标改为本 Fork README 的 Donation 锚点；中英文说明同步维护者提供的地址，并区分 Fork 与上游捐赠。不是新增支付、到账监控或二维码功能。API、数据库、Node/scripts、证书、端口、订阅与核心均无变化；[变更及发布证据](docs/DONATION_LINK_RELEASE.md)。

## MR-20261003-EGRESS-UDP（镜像已发布，服务器验收待完成）

每个 Node 的住宅出口新增 UDP 处理；保留原主题、证书、端口及原表单宽度。`legacy` 保持原样，`proxy` 要求 SOCKS 供应商支持 UDP，`tcp_only` 默认 DNS 经住宅代理 TCP、其他默认 UDP 阻断。原显式路由优先，不新增直连降级；不是通用 UDP 转 TCP。主面板增加 `udp_mode` 和 additive 迁移；新模式要求配对 Node `managed-outbounds-udp-v1`。主面板/Node 都需配对更新，scripts 运行时无变化、配对文档已更新，核心仍 v26.3.27。测试与限制见 [功能合同](docs/NODE_EGRESS_UDP.md)；真实 UI/手机/供应商验收待完成，下方历史发布记录不包含本功能。

发布证据（配对源 SHA、Actions、两镜像 index/架构 digest/OCI revision、scripts 文档提交）见 [EGRESS_UDP_RELEASE.md](docs/EGRESS_UDP_RELEASE.md)。服务器未验收，不是稳定版。

## 2026-10-03 订阅兼容修复（镜像已发布，服务器验收待完成）

`reject_new` 不再拒绝不带 `X-HWID` 的普通客户端：返回原共享凭据，主核心与 Node 保留该共享账号。带 HWID 的请求仍按登记额度生成/复用独立凭据，超额的新 HWID 返回 `429`；0 表示不限制登记。无 HWID 的兼容路径不能强制限制设备，也能绕过 HWID 限额。Node ACK 不证明全部客户端被拦截。本轮只改主面板订阅和账号加载/同步，Node 与安装脚本运行时无变化、不需更新；原 UI、数据、证书、端口、环境文件及核心 `v26.3.27` 保留。服务器验收待重新完成，发布证据见发布清单。

发布证据：主面板源 commit `37bab0b113c44ccb2a9db6230ac982b7d2a889a1` / Actions `37090609233` / GHCR `latest` index `sha256:c4bbe88b5b547bbdca3d6b8a4bf1e7c92aeb29ae50b36cd758b7c6eccae2edfc`；配对 Node 源 commit `c135743d1ad26d45538e4c6c7a65a9c6693856a8` / Actions `37090612247` / GHCR `latest` index `sha256:21340918298f0b8647fb7eb360294334891fc219e280a75af5d133c66ee9fbc1`。

## 2026-10-02 发布状态

- 状态：镜像已发布，服务器验收待完成；本地测试和 GitHub Actions 已完成，不能写成“稳定发布”。
- 主面板 `a6efaa8eafd82c3f68d2ff29074cf9eeb1ec8ae0` / Actions `36975384550` / GHCR index `sha256:42af5defdd9f325b0244c4be182ae6f77513d1d4e2d3572ea009215508de8dae`。
- 配对 Node `d6f3bec204a75085939b5b4e25fa6502f5946ae5` / Actions `36975383911` / GHCR index `sha256:f2a9e93ca3168abb3559f3e48baa98d02e6377fb8d4a480407f447a97bbbf774`。
- 正式 Xray 基线为 `v26.3.27`；服务器更新前必须备份数据库、`.env`、证书、Xray 配置和数据卷。

本仓库由 Mr.shaw 基于 [Gozargah/Marzban](https://github.com/Gozargah/Marzban) 开发，供其他使用者按开源许可证使用。感谢原作者和贡献者；保留原有 Git 历史与 AGPL-3.0 许可证。本说明只记录本 Fork 的扩展，不把这些功能描述为上游官方功能。

开发参考原项目 `CONTRIBUTING.md`：后端继续使用 FastAPI、SQLAlchemy 和 Alembic，前端沿用 React/Chakra UI。`kissow/Marzban` 的 `master` 是唯一日常安装、升级和镜像发布源；临时开发分支合并后删除。原作者仓库只保留为历史基线、许可证及致谢来源，普通安装和升级流程不会自动读取其可执行内容。

## 前端主题兼容约束

- 完整保留官方 Marzban 的 Chakra UI 主题配置、颜色 token、字体、深浅色模式和响应式断点；不修改 `app/dashboard/chakra.config.ts` 来为扩展功能另建视觉系统。
- 新增功能只能组合官方 Chakra 组件和项目已有的表单、按钮、提示、Accordion、间距及状态样式，并放入原有 Node 设置流程；不得使用独立 CSS、硬编码品牌色、独立字体或另一套卡片/布局规范。
- 原版节点名称、启用开关、节点地址、节点端口、API 端口、使用系数、证书查看/下载、保存、删除和重连交互必须继续保留。扩展的健康信息和出站配置只是原节点表单中的附加区块。
- 节点未连接时，原节点弹窗在标题栏下方、证书区上方显示后端失败/连接原因；原因为空时显示状态兜底文案。`connecting`/`error` 可从该位置点击原版重连接口，`disabled` 不显示可操作重连按钮。
- `mrshaw-v0.8.4-preview.3` 将节点弹窗最大宽度调整为 860px、指标区域最大宽度调整为 700px；手机端继续使用原视口断点。仅布局变化，不要求更新 Node。
- `mrshaw-v0.8.4-preview.4`（已发布）将节点弹窗最大宽度调整为 800px，刷新按钮移至运行指标标题旁边，五项指标铺满可用内容区，不额外保留右侧空白；原主题、左右内边距、手机端断点和原功能不变。Actions `36726339140` 已发布 `ghcr.io/kissow/marzban:latest`。

## 当前扩展

- `/api/node/{node_id}/health` 经现有 Node 认证通道读取对应节点的 CPU、内存、磁盘和运行时间；过期或无效快照不显示为实时值。
- 节点管理界面展示上述指标。2026-10-02 本地开发版优先读取 Xray `GetAllOnlineUsers`；旧核心回退到 Node 观察到的近期流量，旧 Node 回退到主面板 `NodeUserUsage` 记录。来源、范围、采样时间分别标注，详情见 [活动与策略合同](docs/NODE_ACTIVITY_AND_POLICY.md)。
- `/api/node/{node_id}/egress` 按节点 ID 保存唯一一条 HTTP/SOCKS 出站配置；新增更多 Node 时各自独立配置住宅 IP。凭据加密存储，API 不回显密码；下发时只给该节点的配置副本添加 `marzban_node_extensions` 扩展，不修改主面板 Xray 配置。
- 配置前先通过 Node 健康响应确认 `managed-outbounds-v1` 能力；不支持的旧 Node 不接收新配置。删除出站会触发节点重启以恢复原路由。
- 用户设置新增设备限制字段：`device_limit`、`device_limit_mode`、`device_limit_action`；普通订阅和指定客户端格式订阅可通过 `X-HWID`、`X-Device-OS`、`X-Device-Model` 登记设备，并由 `/device-status` 返回脱敏统计。原始 HWID 只保存 SHA-256 哈希；`reject_new` 超限返回 `429`，`log_only` 只记录不拒绝。
- 设备限制在带 HWID 的订阅请求登记时执行；`reject_new` 为每个已登记 HWID 生成独立协议凭据，并通过现有 Xray 控制通道同步到主核心和已连接 Node。配置同时保留共享账号供普通客户端兼容使用；无 HWID 返回正常订阅，不登记设备，不能保证其限额。带 HWID 的超额新请求返回 `429`，不能靠切换输出格式获得新的独立凭据；共享配置复制使用仍能绕过 HWID 限额。它不是实时在线设备数统计，真实客户端及服务器仍需验收。

设备限制代码已完成；历史专项测试为 5 passed、历史完整测试为 22 passed，本轮主面板完整 pytest 为 43 passed，Node 为 39 passed，SQLite 迁移升级/回滚也已通过。2026-10-01 的正式 Actions 记录保留为历史证据；本轮新增的设备专属凭据与 Node 配置加载尚未完成新的 Actions、镜像和服务器验收，因此当前仍是测试版，不是 Xray 实时连接数限制。

住宅出口功能必须与同一开发系列的 `kissow/Marzban-node` 配对。legacy 模式下 HTTP 代理只承载 TCP，UDP 保持原路由；本地未发布的新模式行为见上方合同。尚未实现住宅代理自动健康检查、故障摘除、按用户/分组路由及精确实时设备数限制。新增 Node 活动统计仍需配对镜像与真实服务器验收。

节点指标只由 Marzban 向 Node 通过现有认证通道读取，并由 Marzban 的受保护 API 提供。任何获授权的外部项目均可独立调用该 API；本仓库不包含特定业务系统的对接、别名映射或页面代码。

接口用途、`.env` 配置与 API 的区别，以及每次改动必须同步维护文档的发布流程，见 [Mr.shaw 扩展接口与更新规范](MR_SHAW_API_AND_RELEASE.md)。

## Xray 核心版本与功能边界

仓库正式构建基线统一为 `v26.3.27`（稳定版）。主面板和 `Marzban-node` 的 Dockerfile、GitHub Actions 以及安装脚本都通过 `XRAY_CORE_VERSION` 固定到同一版本；不再使用会随时间漂移的 `latest` 核心。`v25.3.6` 和 `1.8.24` 只属于历史 UI 预览示例，不是可安装核心版本。

`v26.9.9` 当前是 Xray-core 的预发布版本，发布说明没有独立的稳定变更清单并指向后续预发布版本。因此它不能直接替换正式镜像的 `latest`，也不能因为核心版本号变大就直接在面板增加一批开关。核心支持某项协议，只表示 Xray 能解析该配置；要成为面板功能，必须同时具备：Marzban 配置模型、配置生成/订阅转换、Node 下发与重启预检、前端表单、客户端兼容性测试和回滚说明。

当前正式版只开放已在本仓库端到端验证过的功能：原有官方入站/订阅能力、REALITY/TLS/WS/gRPC/TCP 等现有配置，以及每个 Node 独立的住宅代理出站。Hysteria 2、Finalmask、XHTTP/3、ECH、WireGuard 等核心能力暂不自动显示为新面板选项；它们需要单独完成配置模型、订阅格式、Node 兼容和客户端测试后，才进入测试版，再决定是否纳入正式版。

如需验证 `v26.9.9`，只能生成独立测试标签（例如 `xray-26.9.9-test`），不覆盖 `latest`，并记录主面板、Node、Xray 配置预检、订阅客户端、回滚和数据卷检查结果。服务器上的 `core-update` 会修改外部 Xray 二进制，可能覆盖容器内版本；生产环境以仓库镜像固定版本为准，禁止把一次手动 `core-update` 当成仓库版本。
## 本地验证

主面板 Python 单元测试：`python -B -m unittest discover -s tests -v`。管理端执行 `tsc --noEmit` 和 `vite build`。Alembic 迁移需在备份后的测试数据库先升级、回滚，再验证原有节点与用户数据。Node 端还需用其配套测试和 Xray 二进制预检。
