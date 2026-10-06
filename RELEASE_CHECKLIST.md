# Marzban 主面板发布清单

## MR-20261006-CONTROL-RESILIENCE（镜像已发布，服务器验收待完成）

- [x] 主控会话保留、只读有限重试、健康退避/并行、多用户同步和流量/日志隔离；无 UI/数据/端口/证书/HWID/Xray 修改。
- [x] 最终同一运行时代码完整回归两轮 116/116；20 项韧性及 13 项真实传输各再连续三轮；compileall、pip check、固定入口 Check/diff 通过。
- [x] README/FORK_FEATURES/CHANGELOG/接口/更新流程及工作区 05/08/09 更新，Node/scripts 明确无变化。
- [x] 用户授权后的推送、PR #12 合入 `eb43761e`；正式 Actions `37486719383` 成功，本轮新镜像 index/双架构 manifest/config/OCI revision 核对。
- [ ] 升级前备份、主控更新、本轮运行 revision 核对与至少 30 分钟真实网络/客户端验收。

已切换 Fork 的主控可用 `marzban update` 获取本修复；Node/scripts 不需本轮更新。镜像已发布不等于服务器已更新或链路稳定；证据回写为仅文档 `[skip ci]`，不改变已验证运行时 revision。[精确摘要、SSH 命令与验收标准](docs/NODE_CONTROL_RESILIENCE.md)。

## MR-DASHBOARD-I18N-MOBILE（镜像已发布，服务器/视觉验收待完成）

- [x] 原 React/Chakra 局部修改，主题、协议、证书、端口、数据保留。
- [x] 四语言/时间/原表单/API 枚举/响应式源代码约束回归 34/34；主控完整回归 95/95。
- [x] TypeScript、生产与原组件预览构建通过；README/功能/更新/API 文档与工作区 05/08/09 补充。
- [ ] 原组件实际浏览器 320/375/390px、桌面、深浅主题视觉核对。当前安全策略校验无法授权，不能用代码测试代替。
- [x] 2026-10-06 用户明确要求上传/构建，授权先发布；实际视觉验收仍待完成，未登记为通过。
- [x] PR #11 合入 master `5655213099c18532ff3daff5cead010c181a19e9`；正式 Actions `37353281396` 成功（Linux 95/95、语言 34/34、类型/构建及 Xray 版本闸门）。
- [x] GHCR latest index `sha256:793c61738cf18f8641c2ce4b86037a41064903b7e59e4c49a296f8121c2947ce`；两架构 manifest/config 原始字节哈希、OCI revision 与核对前后 latest 一致，完整证据见详情。
- [ ] 服务器备份/更新、镜像 revision、四语言切换、手机原入站字段/帮助/保存/关闭真实验收。

Node/scripts 无变化、不需本轮更新；本次镜像已发布，不沿用历史镜像证据。文档证据回写 `[skip ci]` 不改变已核对镜像。[详情](docs/DASHBOARD_I18N_MOBILE.md)。

## MR-20261006-NODE-RECOVERY（镜像已发布，服务器验收待完成）

- [x] 生命周期/退避、健康隔离、阶段原因和 TLS 期限修复；原版组件与数据保留。
- [x] 最终同一运行时代码两轮全量 95/95；真实 TLS/mTLS/旧服务兼容、并发/管理路由、恢复与订阅/策略回归通过。
- [x] TypeScript/Vite、compileall、pip check、固定入口 Check/diff 检查通过；既有警告单独记录。
- [x] README/功能/变更/API/流程及工作区 05/08/09 登记；Node/scripts 无线协议或安装变化、不需本轮构建更新。
- [x] PR #10 合并为 `122632c8`；分支 Actions `37340492999` 与 master Actions `37340574125` 成功，Linux 全量 95/95；双架构镜像/OCI revision 核对通过。
- [ ] 主控更新、原版重连/自动恢复、故障 message、订阅/真实应用访问验收：未执行。

[本轮新摘要、发布证据与验收范围](docs/NODE_RECOVERY_RELEASE.md)。镜像已发布不代表服务器已更新；未执行镜像本地启动或生产网络故障注入验收。

## MR-20261003-SCHEDULER-DEPENDENCY（镜像已发布，服务器验收待完成）

- [x] APScheduler `3.11.3` 已替换旧 `3.9.1.post1`；不再依赖 `pkg_resources`，Docker 不再锁定旧 setuptools。
- [x] 调度器 API、UTC 任务注册/退出和主控完整 unittest `69/69` 通过，含 6 项调度器回归。
- [x] TypeScript/Vite 生产构建、pip check 与 git diff 检查通过；既有 chunk 和其他弃用提示单独登记。
- [x] 主控连接修复已加入回归测试：先 connect，再 health/start；失败原因保留。
- [x] API、数据库、Node 运行时代码、证书、端口、用户数据和 Xray `v26.3.27` 无变化；Node/scripts 无需更新。
- [x] 源 `78e7b8e` 已推送；Actions `37135175798` 首次成功，干净 Linux 后端 69/69 与前端检查通过。
- [x] 本轮 GHCR latest index/amd64/arm64 digest 与两架构 OCI revision 已核对，见 [发布证据](docs/NODE_CONNECTION_RELEASE.md)。
- [ ] 主控服务器更新后检查节点初连、原版重新连接、订阅和应用访问；未远程执行更新或验收。已配对 Node 不需再次更新。

发布状态只能在 Actions 和镜像证据核对后更新；本地测试通过不等于线上镜像已发布。

## MR-20261003-DONATION-LINK（2026-10-03）

- [x] 维护者提供地址；中英文 README、前端目标和接口说明保持一致，注明 Fork 受支持方并保留上游致谢/许可证。
- [x] Header/主题/布局无变化；API、数据库、Node 通道、订阅、证书、端口、用户数据和 Xray v26.3.27 无变化。Node/scripts 无需更新。
- [x] 主面板 54 项后端测试、TS/Vite、差异检查、生产 JS 目标和中英文地址一致性检查通过。
- [x] 源提交 e72943b 已推送 master，GitHub API 核对通过；Actions 37123809995 自动触发。
- [x] Actions 37123809995 首次成功，新 latest index/两个架构 digest/OCI revision 均核对本次源 e72943b；证据见发布记录。
- [ ] 服务器更新后点击捐赠入口验收。

实际结果及边界统一登记于 [DONATION_LINK_RELEASE.md](docs/DONATION_LINK_RELEASE.md)，不得把推送完成写成镜像已发布。钱包地址为维护者提供，未做链上归属或转账验证。

## MR-20261003-EGRESS-UDP（镜像已发布，服务器验收待完成）

- [x] 原 Chakra 住宅出口表单增加 per-Node UDP 处理；保留原证书、节点端口、开关和宽度，手机单列。
- [x] 既有 egress API、能力标识、迁移 `7e8f9012ab34` 和密码保留合同已登记；旧数据 legacy，原用户/节点/凭据不删除。
- [x] 主面板 54 项、Node 48 项完整本地测试通过；固定 Xray v26.3.27，含 8 组解析和 4 项实际 DNS TCP 运行测试。
- [x] TypeScript、生产 Vite 和真实原组件预览构建通过；没有新增端口、证书或脚本变化。
- [x] README/FORK_FEATURES/CHANGELOG/API、Node 线协议与工作区 05/08/09 已同步；[边界与验收](docs/NODE_EGRESS_UDP.md)。
- [ ] 真实桌面/手机截图审核：浏览器本地安全策略校验未通过，不能标为 UI 已验收。
- [ ] Linux 主面板/Node 认证联调、实际供应商 TCP53、v2rayNG/Clash Meta 同节点对照与 UDP 支持供应商回归。
- [x] 已获准推送；配对提交、Actions 成功、两镜像 index/架构 digest/OCI revision 已登记。服务器验收仍待完成。

本功能镜像已发布，服务器验收待完成；下方历史验收不能代替本次 UDP 功能验收。需要配对更新 Node 和主面板，优先 Node；scripts 运行时无变化、配对文档已更新。非 DNS UDP 阻断目前由路由单元测试覆盖，不是所有真实应用已验证。

发布证据（配对源 SHA、Actions、两镜像 index/架构 digest/OCI revision、scripts 文档提交）见 [EGRESS_UDP_RELEASE.md](docs/EGRESS_UDP_RELEASE.md)。服务器未验收，不是稳定版。

## MR-20261003-HWID-COMPAT（镜像已发布，服务器验收待完成）

- [x] 修复无 HWID 订阅 428；共享账号与独立账号共同加载、同步到主核心和在线 Node。
- [x] 文档说明无 HWID 兼容路径可绕过限额；HWID 登记不等于物理设备数，ACK 不证明所有客户端被拦截。
- [x] 完整后端测试 49 项、TypeScript/Vite、compileall 与 diff 检查通过；Vite 仅保留既有大 bundle 警告。
- [x] 仓库提交、GitHub Actions、GHCR index/架构 digest 和 OCI revision 已核对。
- [ ] 服务器更新后验证普通客户端导入、真实主核心/Node 连接，以及 HWID 登记/重复/超额拒绝。
- [x] 无新 UI、数据库迁移、Node 通道、脚本、证书、端口、环境文件或核心版本变化；Node 不需更新，核心仍 v26.3.27。

本轮代码和镜像已经发布；先前用户验收后又报告订阅失败，服务器必须按下方验收项重新验证，不能直接标为稳定发布。

发布证据：主面板源 commit `37bab0b113c44ccb2a9db6230ac982b7d2a889a1`，Actions `37090609233`，GHCR `latest` index `sha256:c4bbe88b5b547bbdca3d6b8a4bf1e7c92aeb29ae50b36cd758b7c6eccae2edfc`；配对 Node 源 commit `c135743d1ad26d45538e4c6c7a65a9c6693856a8`，Actions `37090612247`，GHCR `latest` index `sha256:21340918298f0b8647fb7eb360294334891fc219e280a75af5d133c66ee9fbc1`。Node 本轮无运行时代码变化，不需要更新 Node 服务器；两个仓库正式 Xray 均为 `v26.3.27`。

## MR-20261002-01 镜像发布核对（服务器验收待完成）

- [x] 新增 Node 活动/策略合同及真实 RPyC 新旧服务测试；主面板完整 43 项、Node 完整 39 项本地测试通过。
- [x] TypeScript 检查、Vite 本地生产构建通过；原主题、节点弹窗宽度、证书和表单控件保留。
- [x] 健康响应明确来源与执行范围；策略确认未宣称精确设备连接拦截。
- [ ] 原组件桌面/手机截图：浏览器管理策略检查失败，待服务器验收。
- [x] GitHub 推送、Actions 和镜像 digest 已核对；真实服务器验收尚未执行。

发布证据：主面板 commit `a6efaa8eafd82c3f68d2ff29074cf9eeb1ec8ae0`，Actions `36975384550`，GHCR index `sha256:42af5defdd9f325b0244c4be182ae6f77513d1d4e2d3572ea009215508de8dae`；配对 Node commit `d6f3bec204a75085939b5b4e25fa6502f5946ae5`，Actions `36975383911`，Node GHCR index `sha256:f2a9e93ca3168abb3559f3e48baa98d02e6377fb8d4a480407f447a97bbbf774`。两个仓库均固定 Xray `v26.3.27`。状态只能写“镜像已发布，服务器验收待完成”。

本清单适用于 `kissow/Marzban` 的每一次代码、接口、数据库、管理端 UI、配置、Xray 核心或文档更新。它必须和仓库内的 [`docs/REPOSITORY_UPDATE_FLOW.md`](docs/REPOSITORY_UPDATE_FLOW.md) 一起使用；工作区中的 05/06/08/09 项目资料仍可作为扩展记录，但仓库内文档是上传后可复核的最小完整记录。

## 变更登记

- [x] 已记录日期、标题、发布状态和主面板 commit。
- [x] 已标记变更是否涉及 API、数据库迁移、Node 通道、订阅响应、证书、端口、`.env`、Xray 核心和 UI。
- [x] 已确认主面板、Node、脚本是否需要配对发布；没有影响的仓库也写明“无变化”。
- [ ] 没有把 `_patch.tmp`、`ui-preview/`、构建临时目录、数据库、密钥或生产配置加入提交。

## 代码和接口

- [x] 新增、修改或删除的路由已在 `MR_SHAW_API_AND_RELEASE.md` 登记：方法、完整路径、认证、请求、响应、错误码、副作用、Node 兼容、弃用和回滚。
- [ ] `.env.example`、配置表和 README 已同步；真实密码、Token、数据库连接串和代理凭据未进入仓库。
- [x] 数据库变化有 Alembic 迁移、升级前备份、回滚测试和旧用户/节点数据验证。
- [ ] 只改 UI 或文案时明确写出：API、数据库、Node 通道、证书和端口无变化。
- [x] 接口、订阅字段、Node 通道或配置字段变化已同步写入 [`docs/REPOSITORY_UPDATE_FLOW.md`](docs/REPOSITORY_UPDATE_FLOW.md)，并通知 Node/scripts 配对文档。

## 测试

- [x] `python -B -m unittest discover -s tests -v`（本轮 43 项）
- [ ] CI 使用的测试命令与本地测试命令一致；新增测试默认使用仓库现有 `unittest` 规范，未引入未声明的 pytest/fixture 依赖。
- [ ] 干净 CI 安装后导入所有测试模块；旧依赖若使用已移除的兼容模块（例如 `pkg_resources`），必须在依赖文件中显式锁定兼容版本。
- [ ] 单元测试导入数据库/应用模块时不隐式依赖 `/usr/local/bin/xray` 等生产服务；外部二进制依赖必须在测试步骤显式准备或由测试专用桩隔离。
- [x] 管理端 `npm exec tsc -- --noEmit` 和 `npm run build`（package.json 没有 typecheck 脚本）
- [x] `git diff --check`
- [ ] 订阅、二维码、用户到期、节点、证书和端口回归通过。
- [x] Node 配对契约、健康状态、住宅出口（如适用）和失败回滚通过。
- [ ] 桌面和手机视口真实渲染通过；记录视口、缩放、截图和是否横向溢出。

## CI、镜像和发布

- [x] GitHub Actions 成功，记录 workflow、run ID、源 commit 和失败重试结果。
- [x] 如 Actions 失败，记录失败步骤、根因、修复提交和重新构建结果；失败状态不得写成镜像已发布。
- [x] `ghcr.io/kissow/marzban` 的 tag/index digest、amd64/arm64 digest 与 OCI revision 对应源 commit。
- [x] 镜像能在干净环境拉取并启动；没有把 Actions 排队或代码已推送误写成已发布。
- [x] `CHANGELOG.md`、`FORK_FEATURES.md`、README、接口文档和项目验收清单状态一致。

## 问题复盘与防复发（强制）

- [ ] 每个失败 run 都登记：日期、run ID、失败 job/step、完整错误摘要、根因、修复 commit、复跑 run 和最终结论。
- [ ] 每个根因都转换为一个可执行的闸门（测试命令、依赖锁定、导入隔离、镜像摘要核对或服务器验收项），不能只写“已修复”。
- [ ] 复跑必须从干净 CI 环境开始；本地通过、代码已推送或 Actions 已排队都不能替代成功证据。
- [ ] 发布前复查历史问题登记，确认本次没有重新出现同类错误；若再次出现，追加同一问题的复发记录，不覆盖旧记录。

## 服务器验收与回滚

- [ ] 服务器更新前完成数据库、`.env`、证书、Xray 配置和数据卷备份并记录位置/校验。
- [ ] 官方旧安装只执行 `adopt`；已切 Fork 的安装只执行 `update`；新机才执行 `install`。
- [ ] 更新后验证容器、日志、用户、订阅、节点、证书、端口、出站和手机/桌面页面。
- [ ] 明确回滚镜像/tag 和数据库恢复方式；不执行 `docker compose down -v`，不删除 `/var/lib/marzban`。
- [ ] 服务器截图和日志验收完成后，才把状态改为“稳定发布”。

## 发布记录最小字段

```text
主面板 commit：
配对 Node commit：
配对脚本 commit：
Actions run：
GHCR index/架构 digest：
OCI revision：
Xray 版本：
API/数据库/Node 通道变化：
测试结果：
服务器验收结果：
已知限制与回滚方式：
```
