# Mr.shaw Fork 更新、接口与验收登记

## MR-20261008-NODE-RELAY-SOURCES（镜像已发布，服务器/视觉验收待完成）

连接方式采用原React/Chakra独立管理弹窗和原信息图标。可选择Marzban主服务器或另一台源Node中转到目标Node；保留原订阅别名、顺序、数量，只替换精确匹配的端点，不新增Relay。目标认证、设备凭据和出口不变。自转发/环路/占用/能力/精确ACK/失败回滚、来源隔离与恢复有回归测试。

管理API增加source/source_node_id/来源列表，additive迁移9012ab34cd56；Node新增managed-node-relay-v1、原认证REST/RPyC完整快照与独立转发进程。固定Xray26.3.27，原证书、控制/API端口、用户、.env与数据卷保留。首版VLESS TCP/RAW REALITY、IPv4/DNS-only入口、单跳选择，不是所有协议或任意UDP转发；每源512个配置不是吞吐承诺。

本地最终代码和独立发布副本再次复测：主控164/164、Node60/60（准备固定Xray，无跳过）、前端47/47、类型/生产构建、依赖/diff通过。干净Linux CI与两镜像双架构发布核对完成；真实跨服务器mTLS、公网吞吐、多引擎数据库、实际原组件UI截图仍待验收，不标稳定版。UI截图因浏览器策略blocked，未绕过。

主控revision 93bfbb5b17dd8ee731449976df1a4af4e0f57ca5，Actions37657985804；Node revision 7b45fc0dc3b4451045a06123b52ccdaaa5911b8d，Actions37657976968。scripts合并ed274ba82410f9e6f580cbec59b2a15a89ab81ea，Actions37657994843成功，脚本运行时不变。先在承担来源的Node运行marzban-node update，再在主控运行marzban update；仅作目标的既有配对Node不强制更新。新Node沿用仓库install，现在拉取新latest；旧机不重装、不删卷、不重复adopt。源业务入口TCP需放行，客户端刷新订阅。

[精确配对SHA、index/架构/config摘要、接口与SSH验收证据](https://github.com/kissow/Marzban/blob/master/docs/NODE_RELAY_SOURCES_RELEASE.md)。下方旧记录只描述各自日期的阶段，不代替本轮最新状态；文档[skip ci]提交不改变已核对的运行时镜像revision。


## MR-20261007-RELAY-INTERNAL-SUBSCRIPTION（本地完成，未发布）

订阅按原 Host 精确匹配，仅换地址/端口，不追加中转条目或重命名。原存储和转发保持，short ID 使用输出副本；API新增校验不新增字段/迁移。最终后端149/149两轮、前端45/45、类型/构建/依赖/diff通过。Node/scripts无变化，不需服务器更新。Node→Node作为后续扩展，当前source仍仅main。公开文档和工作区05/08/09已更新；本次尚未推送/构建/验收，不复用d2350203旧镜像作为修复证据。[合同和发布门槛](NODE_RELAY_SUBSCRIPTION.md)。

## MR-20261007-NODE-RELAY（镜像已发布，服务器待验收）

开源文档统一使用“Marzban 主服务器中转到 Node 节点”，不将主服务器所在地区作为前提。配置、拓扑、示例、安装、测速和验收均以主服务器/目标Node说明；示例域名使用main.example.com等通用占位，不绑定特定维护者或国家/地区。

主服务器可选每 Node TCP 中转，首版仅 VLESS TCP/RAW REALITY、IPv4 入口。原直连条目、用户凭据、REALITY 参数、证书、Node 控制/API/倍率/住宅出口保留；Node/scripts 无本轮运行时或命令变化、不需服务器更新，Xray 固定 v26.3.27。新增四个 sudo API、node_relays additive 迁移 8f9012ab34cd、独立进程及失败恢复；running 仅代表本地监听就绪。 API/迁移/回滚/兼容和工作区05/08/09已登记。

用户已授权先发布。源 134f12faf5e29e53986ff271a8c8f57b8a38db38，PR #16 合入 d23502030358930592016f9ff2f7d3f42acad4e7；PR CI 37637526876 成功（140 项普通后端 + 两项显式真实 Linux Xray、前端44/44、类型/生产构建），本地最终142/142及前端44/44复核通过。正式 Actions 37637973415 首次成功；latest index sha256:252adac60cdcbcc83a7ef13a080d52876876017a65220c58fcf76539db9ccd03 与 amd64/arm64 manifest/config/OCI revision 已核对（d23502030358930592016f9ff2f7d3f42acad4e7）。仅文档回写 [skip ci] 不改变该运行时版本。UI 截图受浏览器管理策略阻止，服务器、公网 REALITY/手机与实际提速仍待验收，不冒称稳定发布。 [详细证据、服务器流程与测速](NODE_RELAY.md)。

## MR-20261007-BROWSER-TRANSLATION（镜像已发布，服务器验收待完成）

浏览器翻译 opt-out 与原 HostsDialog 动态状态文本包装；原主题、宽度、四语言和表单保留。主控 hosts/inbounds API、数据、证书、端口、Node 协议、HWID/UDP、Xray v26.3.27 不变，Node/scripts 无本轮运行时或命令变化。本地/干净 Linux 前端 40/40、后端 116/116、TypeScript/生产构建通过；PR #14 合入 96599563、正式 Actions 37494615636 成功，latest index/双架构 OCI revision 已核对。服务器验收待执行，不能用历史发布摘要代替；仅文档 [skip ci] 回写不重建镜像。[本轮精确证据和范围](BROWSER_TRANSLATION.md)。

## MR-20261006-CONTROL-RESILIENCE（镜像已发布，服务器验收待完成）

本轮仅主控运行时代码：慢 TLS/控制链路容错、保留认证会话、只读有限重试、健康退避而不盲目重启、并行健康及单快照设备账号同步、流量/日志异常隔离。API/schema/UI/证书/端口/HWID/Xray 不变；Node/scripts 无运行时/协议/命令变化，不需本轮配对更新。两轮完整 116/116、20/20 韧性与 13/13 真实传输各再复跑三轮；固定入口、依赖和语法检查通过。PR #12 合入 `eb43761e`，正式 Actions `37486719383` 成功，本轮 latest index 与双架构 OCI revision 已核对；服务器状态仍待用户更新/验收，不能引用历史 digest 或把发布当作上线验收。证据回写仅文档 `[skip ci]`，不重建已验证镜像。具体合同/证据见 [本轮登记](NODE_CONTROL_RESILIENCE.md)。

## MR-DASHBOARD-I18N-MOBILE（镜像已发布，服务器/视觉验收待完成）

主控原前端四语言与手机入站宽度修复；Node/scripts 无代码/协议/命令变化。API/迁移为“无”：status 英文枚举与 hosts GET/PUT 合同不变。本地语言 34/34、主控 95/95、TypeScript/生产/原组件预览构建通过。

2026-10-06 用户明确要求上传/构建，按授权先发布；浏览器安全策略校验无法授权，实际原组件视觉验收仍待完成，不登记为通过。发布前复核与 Linux CI 34/34、95/95、类型及生产构建通过；PR #11 合入 `56552130`、Actions `37353281396` 成功，latest 双架构 digest/OCI revision 已核对。服务器验收待完成；文档证据回写使用 `[skip ci]`，镜像 revision 仍为运行时合并提交，不冒充文档提交。[完整证据与更新命令](DASHBOARD_I18N_MOBILE.md)。

## MR-20261006-NODE-RECOVERY（镜像已发布，服务器验收待完成）

本轮只改主控恢复代码与测试/文档：每节点生命周期互斥、健康隔离、安全重试、TLS 阶段期限和原 message 原因。最终同代码两轮全量 95/95，前端构建及依赖/语法/diff 检查通过；Node/scripts 无运行时/协议/命令变化，无需本轮构建更新。

已完成 README、FORK_FEATURES、CHANGELOG、接口和发布清单，以及工作区 05/08/09。PR #10 已合入 master `122632c8`；分支 Actions `37340492999`、master Actions `37340574125` 均成功，Linux 95/95 与生产前端构建通过。新 latest index `sha256:ecbe03895e28c1dd7d9441907f967b1806f105e00e01d4dc36232bf7f39bb42b` 及两架构 OCI revision 已核对；服务器部署/验收未执行。证据回写为仅文档 `[skip ci]` 提交，不重建已核对镜像；下方历史记录不替代本轮证据。[本轮记录](NODE_RECOVERY_RELEASE.md)。

## MR-20261003-SCHEDULER-DEPENDENCY：调度器与 Node 初连修复（2026-10-03，镜像已发布，服务器验收待完成）

- 根因：`connect_node()` 在未建立 Node 会话时先调用健康检查，非 legacy 出口首次连接会得到 `Node is not connected`。
- 修复：先调用既有 `node.connect()`，再执行健康/能力检查和 `start()`；异常原因写入节点状态，供原版重连按钮排障。Node 运行时代码不变。
- 依赖：主控 APScheduler 升至 `3.11.3`，移除 `pkg_resources` 弃用路径；调度器 API、UTC 和任务参数保持原样。主控完整测试 69/69、TypeScript/Vite、pip check、diff 检查通过。
- 边界：API、数据库、证书、端口、用户数据、订阅协议和 Xray `v26.3.27` 不变；Node/scripts 本轮无需更新。新提交、Actions、镜像和服务器验收必须单独记录。
- 发布：源 `78e7b8e`、Actions `37135175798` 首次成功，latest index 与两架构 OCI revision 已核对；具体摘要见 [发布证据](NODE_CONNECTION_RELEASE.md)。服务器更新/真实网络验收未执行，不能把镜像发布当作服务器验收。


## MR-20261003-DONATION-LINK：捐赠入口（2026-10-03）

已发布主面板镜像：源 e72943b、Actions 37123809995 首次成功，latest index `sha256:28ffe73996bd0078df894e0d56b0ec742087d678acebd8c8d34b646791f7eb6c`，amd64/arm64 OCI revision 核对通过。服务器点击验收待完成；此轮只更新主面板，Node/scripts 无变化。

主面板只修改前端捐赠常量及中英文 README；补齐更新记录、接口说明和发布清单。Node/scripts 代码与文档合同均无变化，不需配对构建或服务器更新；所有 API、数据库、Node 通道、订阅、证书、端口、环境、数据卷及固定核心 v26.3.27 保持原样。常量变更须构建新主面板镜像，README 推送立即生效但不更新已部署前端。[测试/提交/构建/镜像/服务器记录](DONATION_LINK_RELEASE.md)。

## MR-20261003-EGRESS-UDP：每 Node UDP 兼容（镜像已发布，服务器验收待完成）

主面板：原 Chakra 表单增加 UDP 处理；现有 egress GET/PUT 新增 `udp_mode`，additive 迁移 `7e8f9012ab34`，旧记录 legacy。Node：能力 `managed-outbounds-udp-v1`、配置通道字段和默认 DNS TCP/UDP 路由处理、原子校验。scripts：运行时无变化，配对文档已更新并通过 Actions 检查。证书、端口、环境、数据卷和核心 v26.3.27 保留。不改 HWID 策略。

54 项主面板/48 项 Node 本地测试、TS/Vite/原组件预览构建通过；4 个实际固定 Xray DNS TCP 测试和 8 组解析通过。桌面/手机 UI 截图受浏览器策略限制未验收；Linux 和实际供应商/手机应用尚待验收。**两仓库已推送、Actions 成功、latest 镜像及 OCI revision 已核对**，发布 SHA/Actions/digest 已登记；不复用下方历史证据。

新模式须先发布并更新配对 Node 再更新主面板；不能给生产提供尚未发布镜像的更新命令。旧模式不下发新字段，新模式保存和连接都检查能力。默认 DNS TCP 不等于任意 UDP 转 TCP；原显式路由优先、自定义 DNS 上游被替换的限制见 [NODE_EGRESS_UDP.md](NODE_EGRESS_UDP.md)。

发布证据（配对源 SHA、Actions、两镜像 index/架构 digest/OCI revision、scripts 文档提交）见 [EGRESS_UDP_RELEASE.md](EGRESS_UDP_RELEASE.md)。服务器未验收，不是稳定版。

## MR-20261003-HWID-COMPAT：订阅兼容修复（镜像已发布，服务器验收待完成）

根因：`reject_new` 对无 HWID 客户端返回 428，同时核心移除了共享账号；不仅不能导入，只修改 428 也不能恢复连接。修复同时覆盖真实订阅路由、初始配置和主核心/Node 增量账号同步。无 HWID 返回共享订阅，HWID 成功登记使用独立凭据，超额新 HWID 429，0 不限制登记。共享兼容路径可绕过限额，不保证物理设备数量；ACK 不是全客户端拦截证明。

主面板：代码及接口文档变化；Node：仅配对文档，运行时代码无变化，不需重新构建或服务器更新；scripts：无变化。没有新增数据库迁移、端口、认证通道或配置参数；UI、证书、环境文件、用户数据、数据卷及固定核心 v26.3.27 保持原样。后端/前端/差异检查、Git push、Actions、GHCR digest 已完成；服务器验收仍待执行，此前服务器通过记录不能代替这次回归验收。

发布证据：主面板源 commit `37bab0b113c44ccb2a9db6230ac982b7d2a889a1` / Actions `37090609233` / GHCR `latest` index `sha256:c4bbe88b5b547bbdca3d6b8a4bf1e7c92aeb29ae50b36cd758b7c6eccae2edfc`；配对 Node 源 commit `c135743d1ad26d45538e4c6c7a65a9c6693856a8` / Actions `37090612247` / GHCR `latest` index `sha256:21340918298f0b8647fb7eb360294334891fc219e280a75af5d133c66ee9fbc1`。Node 本轮无运行时代码变化。

原 2026-10-02 发布记录保留为历史证据；后续以本条及发布清单为最新状态。旧无 HWID 428 / 仅私有账号行为已废弃。API 详情见 [接口文档](../MR_SHAW_API_AND_RELEASE.md)。

## 2026-10-02 发布状态（镜像已发布，服务器验收待完成）

- 主面板 `master`：`a6efaa8eafd82c3f68d2ff29074cf9eeb1ec8ae0`；Actions `36975384550` 成功；GHCR index `sha256:42af5defdd9f325b0244c4be182ae6f77513d1d4e2d3572ea009215508de8dae`。
- 配对 Node `master`：`d6f3bec204a75085939b5b4e25fa6502f5946ae5`；Actions `36975383911` 成功；GHCR index `sha256:f2a9e93ca3168abb3559f3e48baa98d02e6377fb8d4a480407f447a97bbbf774`。
- 两仓库均固定 Xray `v26.3.27`；本地测试、迁移升级/回滚和镜像构建已完成，服务器尚未更新，因此不能标记为稳定发布。

## MR-20261002-01：本地活动与策略同步，未发布

主面板工作基线 `654e6c3`（master），Node 工作基线 `140fecb`（feature/mrshaw-release）；均为本地未提交修改。scripts 运行时代码无变化，配对文档更新。

API 增加活动来源/scope/时间和策略数量/revision/同步时间/执行状态；Node 新增 REST/RPyC 活动与策略方法。设备凭据迁移为 `6d7e8f9012ab_add_device_credentials.py`，原证书、端口、配置目录、数据卷和核心 v26.3.27 保持原样。Node 内部启用 statsUserOnline；依赖新增 grpcio。完整合同见 [NODE_ACTIVITY_AND_POLICY.md](NODE_ACTIVITY_AND_POLICY.md)。

真实 RPyC 的 wait 超时签名及远程字典转换错误已修复并加入合同测试；主面板定期清零流量会干扰增量估算，已优先使用核心在线用户 API，旧核心回退明确标为尽力统计。不得仅靠模拟结果认定协议可用。

页面使用原生产组件预览；浏览器管理策略校验失败导致本轮无法完成截图验收。代码与镜像已发布，但服务器验收仍待后续实际执行，不能标记为稳定发布。

本文把本 Fork 每次更新必须同步的流程、接口登记和本次变更证据放在仓库内，避免依赖工作区外的资料文件。它适用于 `kissow/Marzban`；如果一次变更同时涉及 `kissow/Marzban-node` 或 `kissow/Marzban-scripts`，三个仓库必须记录配对 commit 和兼容性。

## 1. 每次更新必须同步的资料

1. `CHANGELOG.md`：用户可见变化、兼容性、已知限制和发布状态。
2. `README.md` / `FORK_FEATURES.md`：功能边界、安装/更新方式和与官方版本的差异。
3. `MR_SHAW_API_AND_RELEASE.md`：新增、修改、删除的 API、数据库、Node 通道和配置字段。
4. `RELEASE_CHECKLIST.md`：代码、迁移、构建、CI、镜像和服务器验收闸门。
5. 本文：跨仓库登记、接口索引、测试证据、源 commit、镜像摘要和服务器验收状态。

只改 UI 或文档也要明确记录：API、数据库、Node 通道、证书、端口和 Xray 核心无变化。节点状态 UI 若增加失败原因或重连按钮，必须确认仍调用既有重连 API，不能另开监控端口。未完成 CI、镜像或服务器验收时，状态只能写“测试中 / 未发布”，不能给生产服务器更新命令。

## 2. 当前变更登记卡

```text
变更编号：MR-20261001-DEVICE-LIMIT
日期：2026-10-01
标题：在官方 Chakra 用户结构中加入用户级 HWID 设备登记限制
状态：测试版镜像已发布，服务器验收待完成

主面板：kissow/Marzban
Node：kissow/Marzban-node（无变化，不需要配对更新）
脚本：kissow/Marzban-scripts（无变化）
数据库迁移：4a9d2e8b7c61_add_user_device_limit.py、6d7e8f9012ab_add_device_credentials.py
Xray：v26.3.27，保持正式基线，不升级 v26.9.9
证书、端口、.env、数据卷、支付：无变化
```

## 3. 本次接口索引

### 用户字段

原有用户创建/修改 API 承载以下字段：

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `device_limit` | integer | `0` | `0` 表示关闭限制 |
| `device_limit_mode` | enum | `hwid` | 当前按订阅请求中的 HWID 登记 |
| `device_limit_action` | enum | `log_only` | `log_only` 只记录；`reject_new` 超限拒绝新设备 |

### 订阅请求

| 方法和路径 | 请求 | 成功/错误 | 兼容性和副作用 |
| --- | --- | --- | --- |
| `GET /{XRAY_SUBSCRIPTION_PATH}/{token}` | 可选 `X-HWID`、`X-Device-OS`、`X-Device-Model`；原始 HWID 最多 512 字符 | 正常返回原订阅；空或超长 HWID 为 `400`；`reject_new` 新设备超限为 `429` | 不带 `X-HWID` 的旧客户端保持原行为；不修改已导入配置 |
| `GET /{XRAY_SUBSCRIPTION_PATH}/{token}/{client_type}` | `client_type` 可为 `sing-box`、`clash-meta`、`clash`、`outline`、`v2ray`、`v2ray-json` | 与普通订阅共用登记逻辑 | 不能通过切换订阅格式绕过限制 |
| `GET /{XRAY_SUBSCRIPTION_PATH}/{token}/device-status` | 无请求体 | 返回限制、已登记数量、剩余数量和支持状态；不返回原始或哈希 HWID | 订阅 token 认证；只读，不新增公网端口 |

服务端按 `(user_id, SHA-256(HWID))` 去重，因此同一 HWID 更换公网 IP 不新增设备；同一公网 IP 下不同 HWID 分别计数。原始 HWID 不落库，OS/型号仅保存截断后的值。

### 数据库

迁移 `4a9d2e8b7c61_add_user_device_limit.py` 与 `6d7e8f9012ab_add_device_credentials.py` 新增用户字段、`user_devices` 表、设备凭据 JSON 和 PostgreSQL 枚举。删除用户会级联清理设备记录；撤销设备后可以重新登记。回滚前必须备份数据库，禁止删除数据卷。

## 4. 已完成的本地证据

- `python -m compileall -q app`：通过。
- 完整后端测试：本轮 `pytest` 43 项通过；历史 `unittest discover` 22 项记录保留为旧阶段证据。
- 设备限制与设备凭据加载专项测试：通过；历史设备限制专项记录为 5 passed。
- 前端 TypeScript 检查和 `npm run build`：通过。
- Alembic：`6d7e8f9012ab` 为设备限制链最新 head。
- SQLite upgrade/downgrade：通过。
- `git diff --check`：通过。

以下仍未完成：PostgreSQL 真实迁移、Linux 隔离环境、并发锁验证、V2RayN/Clash/Hiddify/Shadowrocket 的真实 HWID 兼容矩阵和生产服务器验收。因此本次只标记为“测试版镜像已发布”，不能标记为稳定发布。此前 Actions run `36832627106` 因专项测试误用未声明的 pytest 而失败，run `36835708735` 又发现锁定 APScheduler 导入 `pkg_resources`、但新版 setuptools 已移除该模块，run `36836757035` 再发现测试导入数据库模型隐式调用 `/usr/local/bin/xray`；三轮失败及修复方式均保留在 `CHANGELOG.md`，避免只依赖本地环境或误把“代码已推送”当成“镜像已发布”。

## 5. 本次成功构建与防复发证据

- Actions run：`36838046078`；源 commit：`071819b1d90ca5bcf9dac903d11748ac8080dec7`。
- `ghcr.io/kissow/marzban:latest` OCI index：`sha256:290994ba997ed3120e494814717520db6216d9b615df4b54bc6f8bf147771b07`。
- 架构清单：amd64 `sha256:e17e7dab19d8cf637e2586b65a913ec9c2c758708628be31115411dece67a7e7`；arm64 `sha256:49b1183f193113cdb6c0b5e4d8254b86bce6c0d56e261ec3fe0032fd423c5ff9`。两者 OCI revision 均为 `071819b1d90ca5bcf9dac903d11748ac8080dec7`。
- 成功步骤包括后端 `unittest`（22 tests，`OK`）、前端类型检查/构建、Xray 版本闸门、多架构 Docker 构建和 GHCR 发布。
- 固定防复发闸门：失败必须登记 run、步骤、根因、修复提交和复跑结果；新增测试必须使用 CI 实际命令；依赖必须在干净环境安装；测试导入不得隐式要求生产二进制；发布后必须核对 index/架构 digest 与 OCI revision，最后才允许进入服务器验收。

## 6. 发布顺序

1. 先更新代码、接口文档、CHANGELOG、README/FORK_FEATURES 和本登记卡。
2. 执行后端测试、前端构建、迁移升级/回滚和 `git diff --check`。
3. 在功能分支提交并推送；CI 成功后核对源 commit、镜像 tag、index/架构 digest 和 OCI revision。
4. 仅在镜像证据齐全后进入隔离服务器，先备份数据库、`.env`、证书、Xray 配置和数据卷。
5. 已切换 Fork 的安装使用 `marzban update`；官方旧安装首次切换使用 `marzban adopt`；新服务器才使用 `install`。
6. 服务器验收用户、订阅、节点、证书、端口、日志和手机/桌面页面后，才允许把状态改为稳定发布。

不得使用 `docker compose down -v`，不得覆盖 `.env`，不得删除 `/var/lib/marzban*`，不得把未发布代码直接覆盖正式 `latest`。

