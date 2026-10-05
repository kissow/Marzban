# Mr.shaw Marzban Fork 更新记录

## MR-DASHBOARD-I18N-MOBILE（镜像已发布，服务器/视觉验收待完成）

- 修复选择语言后在线/到期、状态筛选、日历与部分提示仍为英语，补齐原四语言词典/复数。
- 修复状态筛选值误绑定 sort，传给 API 的 status 枚举不变；原 hosts 必填提示在验证时读取当前语言。
- 原入站弹窗桌面保持 440px、手机左右留 12px；内容随容器收窄，长标题/帮助/原操作行换行。
- 新增 34 项回归并接入原 CI，本地主控 95 项、TypeScript、生产与原组件预览构建通过。
- 无 API/schema/认证/端口/证书/Node/scripts/Xray 变化，无新外部源码借入；原主题与作者归属保留。
- PR #11 已合并为 `5655213099c18532ff3daff5cead010c181a19e9`；分支 Actions `37352009623` 和正式 Actions `37353281396` 成功（Linux 95/95、语言 34/34、类型/生产构建与 Xray 闸门通过）。latest index `sha256:793c61738cf18f8641c2ce4b86037a41064903b7e59e4c49a296f8121c2947ce`，两架构 digest/OCI revision 已核对。
- 镜像推送日志为 `2026-10-05T18:16:26Z`（UTC，香港 2026-10-06）。浏览器安全策略校验无法授权，实际手机视觉与服务器验收待完成；不是稳定发布声明。详情 `docs/DASHBOARD_I18N_MOBILE.md`；发布证据仅文档回写使用 `[skip ci]`，不重复构建运行时代码。

## MR-20261006-NODE-RECOVERY：节点卡住/恢复风险修复（镜像已发布，服务器验收待完成）

- 每 Node 连接/重启/修改/删除互斥，重复重连合并，自动退避与手动重试分开；失败不无条件 disconnect 停核心。
- 健康检查隔离异常并覆盖未创建 transport 的启用节点；健康恢复清旧状态，不反复写健康节点状态。全用户账号协调不占节点生命周期锁。
- 控制会话、TLS、配置、API readiness 等阶段错误使用原 message；REST/RPyC 取证书及 RPyC TCP/TLS 加阶段期限，保留 mTLS/证书校验与旧 Node 兼容，失败连接关闭。
- 最终代码两轮全量 95/95 通过；Python/TypeScript/Vite/pip/diff 检查通过。既有弃用和 chunk 告警单独保留。
- UI/API/schema/线协议、证书、端口、用户数据、HWID/UDP 及固定核心 v26.3.27 未改；Node/scripts 无需本轮更新。
- PR #10 已合并，源 `122632c8df4b57c43706cb59fb183e7386004ce1`；Actions `37340574125` 首次成功，Linux 95/95、前端生产构建与 Xray 版本闸门通过。latest index `sha256:ecbe03895e28c1dd7d9441907f967b1806f105e00e01d4dc36232bf7f39bb42b`，amd64/arm64 摘要与 OCI revision 已核对。Actions 上传证据为 `2026-10-05T16:33:03Z`（UTC）。
- 服务器部署与真实网络验收未执行；[日志证据、架构摘要、兼容边界和验收清单](docs/NODE_RECOVERY_RELEASE.md)。后续发布证据提交仅改文档，使用 `[skip ci]` 保留本轮已核对镜像，不把文档提交冒充镜像源提交。

## MR-20261003-SCHEDULER-DEPENDENCY：移除 APScheduler `pkg_resources` 弃用警告（2026-10-03）

- 将 `APScheduler` 从 `3.9.1.post1` 升级并锁定到 `3.11.3`。新版使用 `importlib.metadata`，不再导入已弃用的 `pkg_resources`；不是屏蔽警告。
- 移除 requirements 中的 `setuptools<81` 兼容上限和 Docker 中为旧调度器单独安装 setuptools 的步骤。调度器仍使用原有 BackgroundScheduler、UTC、interval、coalesce 和 max_instances 设置。
- 已验证调度器启动/关闭、UTC 任务注册和项目完整 `unittest discover`（新增 6 项后 69/69）通过；TypeScript/Vite、pip check 和 diff 检查通过。其余 SQLAlchemy/Pydantic 的弃用提示属于独立后续依赖迁移，不影响本次通过结果。
- 主控连接修复同时保留：首次连接先建立 Node 会话，再执行健康检查和启动；失败原因写入节点状态。数据库、用户数据、API 路径、Node 运行时代码、证书、端口和 Xray `v26.3.27` 不变；本轮 Node 无需更新。
- 已发布主控镜像：源 `78e7b8e`、Actions `37135175798` 首次成功，latest index `sha256:9d3b20eba4e19994df9f5170f8ef3a5eaa81c3f846ab12e5f486f2c287bc2880`；两架构 OCI revision 匹配，服务器更新与验收待完成。
- 根因、现有接口执行顺序、跨仓库兼容、依赖升级、测试与发布证据统一见 [NODE_CONNECTION_RELEASE.md](docs/NODE_CONNECTION_RELEASE.md)。历史 setuptools 锁定记录保留作排障历史，不代表当前依赖。

## MR-20261003-DONATION-LINK：捐赠入口指向本 Fork（2026-10-03）

- 按维护者本地修改，将前端捐赠链接指向 `kissow/Marzban#donation`，同步中英文 README 的两组 USDT 地址；BNB Smart Chain 标签规范为 BEP20。
- 明确这些地址支持 Mr.shaw 社区 Fork，保留上游署名、许可证和原项目捐赠说明链接；未修改 Header 结构或 Chakra 主题。
- API、数据库、订阅、Node 通道、证书、端口、环境、用户数据及 Xray v26.3.27 无变化；Node/scripts 无变化，无需更新。主面板常量变更需要新镜像。
- 测试、提交、Actions、镜像和服务器状态分别登记于 [发布记录](docs/DONATION_LINK_RELEASE.md)；不沿用前一功能的镜像证据。
- 发布完成：源 e72943b、Actions 37123809995 首次成功，latest index `sha256:28ffe73996bd0078df894e0d56b0ec742087d678acebd8c8d34b646791f7eb6c`，amd64/arm64 revision 均核对通过；服务器点击验收待完成。

## MR-20261003-EGRESS-UDP：每个 Node 独立 UDP 处理（镜像已发布，服务器验收待完成）

- 原 Chakra 住宅出口表单新增 UDP 处理：默认保持原样、SOCKS TCP/UDP、仅 TCP 兼容；桌面三排双列，手机单列，未修改证书、节点端口或原弹窗宽度。
- 既有 egress API 新增 `udp_mode`；新增仅添加字段的迁移 `7e8f9012ab34`，旧配置默认 legacy、密码加密与留空保留规则不变。
- 非 legacy 必须配对 Node 的 `managed-outbounds-udp-v1`，保存前及重连时检查。兼容模式 DNS 经住宅代理 TCP，其他默认 UDP 阻断；原显式路由保留，不保证任意 UDP 应用可用或全流量防泄漏。
- 主面板 54 项、Node 48 项本地测试通过；TS/Vite/真实原组件预览构建通过，截图审核、Linux/实际供应商/手机验收待完成。两个仓库已推送，Actions 成功，latest 镜像及 OCI revision 已核对；不复用下方历史 digest。
- 主面板和 Node 均有运行时变化，需配对更新；scripts 运行时无变化，配对文档已更新并通过 Actions 检查，Xray 保持 v26.3.27。合同与边界见 [NODE_EGRESS_UDP.md](docs/NODE_EGRESS_UDP.md)。

发布证据（配对源 SHA、Actions、两镜像 index/架构 digest/OCI revision、scripts 文档提交）见 [EGRESS_UDP_RELEASE.md](docs/EGRESS_UDP_RELEASE.md)。服务器未验收，不是稳定版。

## 2026-10-03 普通订阅客户端兼容修复（镜像已发布，服务器验收待完成）

- 修复开启 `reject_new` 后普通客户端因不带 `X-HWID` 而全部收到 `428`、无法导入订阅的问题；无 HWID 请求恢复原共享凭据订阅，不登记设备。
- 同时恢复主核心与 Node 的共享账号加载和增量同步，避免只修 HTTP 响应导致“能导入但无法连接”。已登记 HWID 仍使用稳定的独立协议凭据，超出登记额度的新 HWID 仍返回 `429`；`device_limit=0` 不限制登记数量。
- 明确兼容边界：不带 HWID 的客户端走共享账号，不能强制执行 HWID 限额，也能绕过这一限额。登记数量不是物理设备数或实时在线数；Node 策略 ACK 不是所有客户端被拦截的证明。
- 新增真实 ASGI 路由回归、共享/独立账号同步与 XTLS 传输规则测试；没有 UI、数据库迁移、Node 通道、脚本、证书、端口、环境文件或核心版本变化，Xray 仍为 `v26.3.27`。
- 本条替代下方历史条目的“必须 HWID / 只加载设备账号 / 无 HWID 返回 428”行为。服务器先前确认后又报告订阅失败，故本轮服务器验收重新待完成；不能沿用此前通过结论。
- 发布证据：主面板源 commit `37bab0b113c44ccb2a9db6230ac982b7d2a889a1`、Actions `37090609233`、GHCR `latest` index `sha256:c4bbe88b5b547bbdca3d6b8a4bf1e7c92aeb29ae50b36cd758b7c6eccae2edfc`；配对 Node 源 commit `c135743d1ad26d45538e4c6c7a65a9c6693856a8`、Actions `37090612247`、GHCR `latest` index `sha256:21340918298f0b8647fb7eb360294334891fc219e280a75af5d133c66ee9fbc1`。两个仓库正式 Xray 均为 `v26.3.27`。

## 2026-10-02 设备专属凭据与 Node 新连接拒绝（镜像已发布，服务器验收待完成）

> 历史行为：无 HWID 拒绝与共享账号移除已被 2026-10-03 兼容修复取代。以下保留历史发布证据，不代表最新功能边界。

- `reject_new` 用户按 HWID 生成独立的 VMess/VLESS UUID 或 Trojan/Shadowsocks 密码；订阅请求必须带 `X-HWID`，超额或未登记设备不会获得新的订阅凭据。
- 主核心和每个已连接 Node 只加载已登记设备账号，不再为 `reject_new` 用户加载共享基础账号；切回 `log_only` 时清理设备账号并恢复共享账号。
- 新增 `user_devices.credentials` 迁移 `6d7e8f9012ab_add_device_credentials.py`；不保存原始 HWID，不改变已有用户、证书、端口或数据卷。
- 本地面板 43 项、Node 39 项测试通过；主面板 commit `a6efaa8eafd82c3f68d2ff29074cf9eeb1ec8ae0`、Node commit `d6f3bec204a75085939b5b4e25fa6502f5946ae5` 已推送到各自 `master`。主面板 Actions `36975384550`、Node Actions `36975383911` 均成功，两个 GHCR `latest` 镜像已发布；真实 Linux Node、客户端矩阵和服务器验收仍待完成，不得视为稳定发布。
- 主面板镜像 index `sha256:42af5defdd9f325b0244c4be182ae6f77513d1d4e2d3572ea009215508de8dae`，amd64 `sha256:5354fb4ae86ac5f1f5fa5634c7704068caafd6c8764aad577c8f3b3df6e3f1ee`，arm64 `sha256:c07e5de4aad0089d4ca63b3baf3440b4e41dbc3bf94a386b0b51e9cdf741481b`；两个架构 OCI revision 均为主面板 commit。配对 Node 的 digest 和 revision 见 Node 仓库发布清单。

## 2026-10-02 Node 活动与策略同步（镜像已发布，服务器验收待完成）

- 健康 API 保留并校验 Node 原生在线用户、旧核心近期流量、策略数量/revision/同步时间和执行范围；仅旧 Node 无活动合同才回退到主面板用量采样。
- 用户创建/修改/删除、Node 连接/重启/重连同步完整脱敏策略；60 秒任务自动补齐并重试。一个批次一次数据库读取，最多并发 10 个 Node，单节点失败不影响用户保存及其他节点。
- 修复真实 RPyC 联调发现的 `AsyncResult.wait(3)` 错误；使用 `set_expiry()` + `wait()`。修复 `dict(netref)` 导致的 ValueError，逐键复制远程字典。两项加入真实 RPyC 新/旧服务合同测试，覆盖健康/活动/策略方法。
- 原 Chakra 组件保留原宽度、证书、端口、使用系数和刷新，只增加在线用户口径和策略状态文案。桌面/手机截图验收受浏览器管理策略校验失败阻止，保留原组件预览供审阅，不计为视觉验收通过。
- 设备 API 的数值范围统一为 0–100000；本条是设备专属凭据实现之前的历史记录，当时没有数据库迁移或凭据替换，策略接收也尚未形成直接连接拦截。后续的“设备专属凭据与 Node 新连接拒绝”条目已补上 `6d7e8f9012ab_add_device_credentials.py` 和按已登记账号生成配置的执行链；阅读本文件时以最新条目为准。
- 本地使用隔离 Python 3.12 与仓库依赖复测；接口/升级/回退和测试说明见 [完整合同](docs/NODE_ACTIVITY_AND_POLICY.md)。本次已随上述配对 commit 推送并完成 Actions/GHCR 发布；服务器尚未更新或验收。

本文件仅记录本 Fork 相对 [Gozargah/Marzban](https://github.com/Gozargah/Marzban) 的改动。原作者、许可证和上游 Git 历史均保留；完整功能边界见 [FORK_FEATURES.md](FORK_FEATURES.md)。

## 测试中：节点连接原因与重连入口、近期活跃用户统计（2026-10-01，未发布）

- 节点弹窗在标题栏下方、证书区上方显示连接失败/连接中/已停用的原因；优先展示后端 `node.message`，为空时使用状态兜底文案。
- `connecting` 和 `error` 状态提供“重新连接”按钮，继续调用原有 `POST /api/node/{node_id}/reconnect`；`disabled` 仅展示停用原因。官方 Chakra UI 结构、证书、端口、启用、保存、删除和原节点字段保持不变。
- 节点健康接口的 `active_users` 由主面板在有 `NodeUserUsage` 小时采样时补充为最近 2 小时有正流量的去重用户；无采样为 `null`，有采样但无符合条件用户为 `0`，不是 Xray 实时在线连接数。
- 本轮仅修改主面板 UI、健康统计及文档；Marzban-Node、脚本、Xray `v26.3.27`、证书、端口、支付和住宅出口通道无代码变化。前端 `tsc --noEmit` 与 `npm run build` 已通过；Python 语法检查和 Node 健康专项测试已通过，设备专项仍受本机依赖环境限制，未发布、未构建镜像、未提供服务器更新命令。

## 测试版：用户级设备登记限制（2026-10-01，CI/GHCR 已发布，服务器验收待完成）

- 在保留官方 Chakra UI、证书、端口、Node 通道、支付和原有用户数据的前提下，在用户创建/编辑窗口的流量字段右侧加入“限制设备”。
- 新增 `users.device_limit`、`device_limit_mode`、`device_limit_action` 与 `user_devices` 表；迁移为 `4a9d2e8b7c61_add_user_device_limit.py`。
- 订阅请求可选携带 `X-HWID`、`X-Device-OS`、`X-Device-Model`；原始 HWID 只保存 SHA-256 哈希。同一 HWID 换公网 IP 不重复计数，同一公网 IP 下不同 HWID 分别计数。
- 新增 `/{XRAY_SUBSCRIPTION_PATH}/{token}/device-status` 脱敏统计；`reject_new` 超限返回 `429`，`log_only` 超限继续放行；普通订阅和显式客户端格式不能通过切换格式绕过登记。
- 不带 `X-HWID` 的旧客户端保持原订阅行为；该功能限制订阅请求登记，不是 Xray 实时连接数，也不能断开已导入配置。
- 本次没有修改 Marzban-Node、Xray `v26.3.27`、证书、端口、支付或住宅出口通道。历史 `unittest discover`（22 passed）与设备限制专项测试（5 passed）记录保留；本轮完整 pytest 43 项、Node 39 项、前端 TypeScript/Vite 构建和 SQLite 迁移升级/回滚均已通过。PostgreSQL、真实客户端、Linux 联调和生产验收仍待完成，因此当前是测试版，不标记为稳定发布。
- 成功发布证据：Actions run `36838046078`，源 commit `071819b1d90ca5bcf9dac903d11748ac8080dec7`；`ghcr.io/kissow/marzban:latest` OCI index digest 为 `sha256:290994ba997ed3120e494814717520db6216d9b615df4b54bc6f8bf147771b07`，amd64 digest 为 `sha256:e17e7dab19d8cf637e2586b65a913ec9c2c758708628be31115411dece67a7e7`，arm64 digest 为 `sha256:49b1183f193113cdb6c0b5e4d8254b86bce6c0d56e261ec3fe0032fd423c5ff9`；两种架构 OCI revision 均为上述源 commit。

## CI 构建问题登记与成功复盘（2026-10-01）

- 正式分支合并提交 `9a040201cbe0bc2e783e4ab44e7069ca6fe443a1` 触发 Actions run `36832627106`，在 `Check backend` 阶段失败，后续前端构建和 GHCR 发布未执行。
- 原因是仓库工作流使用 `python -m unittest discover -s tests -p 'test_*.py' -v`，新增 `tests/test_user_device_limit.py` 却依赖未声明的 `pytest` fixture；干净 CI 环境没有 pytest，导致 `ModuleNotFoundError`。
- 已将专项测试统一改为仓库现有的 `unittest.TestCase`、`setUp/tearDown` 规范，未新增第三方测试依赖；本条修复提交后必须重新跑完整 unittest，再等待 Actions 成功后才允许使用 `latest`。
- 防重复检查：新增测试必须使用 CI 实际执行的测试命令；如果要使用 pytest，必须同时把 pytest 固定写入依赖并修改 CI 命令，不能只在本地环境偶然通过。

### 第二轮 CI 失败复盘（run `36835708735`）

- 第一轮测试框架修复后，正式 Actions 仍在 `Check backend` 阶段失败，前端、Docker 和 GHCR 步骤仍未执行。
- 根因是锁定的 `APScheduler==3.9.1.post1` 仍导入 `pkg_resources`，而 CI 安装的最新版 setuptools 已移除该兼容模块，导致 `ModuleNotFoundError: No module named 'pkg_resources'`。
- 已在 `requirements.txt` 明确加入 `setuptools<81`，让干净 CI 和 Docker 构建使用同一套可复现依赖；这不是跳过测试，也不改变运行时业务逻辑。
- 防重复检查：每次依赖升级或 Python 版本变更后，必须在干净环境执行完整 `unittest discover`；锁定依赖若依赖已移除的兼容模块，必须在依赖文件中显式锁定兼容版本，不能依赖 CI 当时碰巧解析出的 setuptools 版本。

### 第三轮 CI 失败复盘（run `36836757035`）

- 依赖兼容修复后，`unittest` 已开始执行并通过前 17 个测试，但导入设备限制测试时仍失败；前端、Docker 和 GHCR 步骤未执行。
- 根因是该测试直接导入数据库模型，而应用导入链会初始化 Xray；干净 CI 没有 `/usr/local/bin/xray`，因此出现 `FileNotFoundError`。这不是生产镜像缺少 Xray，而是测试没有隔离应用启动副作用。
- 已让专项测试在导入前使用临时 Python 版本桩和仓库测试配置，仅隔离测试导入，不改变 `.env`、Dockerfile、生产 Xray 路径或运行时逻辑。
- 防重复检查：单元测试不得因为导入模型而隐式要求系统服务；必须在干净 CI 中验证测试模块可导入，外部二进制依赖要么由测试步骤显式安装，要么使用仅限测试的隔离桩。

### 成功构建确认（run `36838046078`）

- 修复后的后端测试、前端 TypeScript/Vite 检查与构建、Xray 正式版本校验、多架构 Docker 构建和 GHCR 发布均成功；后端日志确认 `Ran 22 tests`、`OK`。
- 本次问题登记闭环为：失败 run → 根因 → 修复提交（`7cb7117`、`eca8fcb`、`071819b`）→ 完整 CI 重跑 → 镜像 digest/revision 核对。以后不得只看到代码已推送就视为可更新，必须完成同样的闭环。
- 防复发总闸门：新增测试必须匹配 CI 命令；依赖必须在干净环境安装；测试导入不得隐式要求生产二进制；构建成功后必须核对 `latest` 的 index、amd64、arm64 digest 和 OCI revision；所有失败原因必须在本文件和发布流程登记。

## 跨仓库更新规范登记（2026-09-30，文档变更）

- 主面板每次代码、API、数据库、UI、配置、Xray 核心或发布脚本变更，都必须与 `kissow/Marzban-node`、`kissow/Marzban-scripts` 及项目资料的变更登记卡配对记录。
- 本仓库同步维护 `FORK_FEATURES.md`、`MR_SHAW_API_AND_RELEASE.md`、README、测试验收清单、GitHub Actions run、GHCR 镜像 digest 和服务器验收状态；没有对应证据的条目不得写成“已发布”。
- 接口变化必须逐项记录方法、完整路径、权限、请求/响应、错误码、副作用、Node 兼容和回滚方式；仅 UI/文档变化明确标记 API、数据库、Node 通道、证书和端口无变化。
- 统一模板见项目资料 `08-跨仓库更新登记模板.md`，三仓库接口和命令总索引见 `09-接口登记索引.md`。本条只规范记录流程，不新增运行时 API、数据库字段或 Node 通道。

## 正式版核心一致性闸门（2026-09-30，未发布）

- 构建完成后立即读取 Xray 二进制版本，并强制核对为 `v26.3.27`；下载脚本返回错误版本时镜像构建失败。
- GitHub Actions 增加正式版本锁定检查，避免主面板和 Node 的 `latest` 镜像意外混入其他核心。

## Xray 核心正式基线收口（2026-09-30，未发布）

- 主面板 Dockerfile、GitHub Actions 和安装脚本统一锁定 `XRAY_CORE_VERSION=v26.3.27`；不再从 Xray 的动态 `latest` 地址取核心。
- `core-update` 使用同一个仓库锁定版本，并修正完成提示，避免主面板显示为空版本或与镜像版本不一致。
- 保留显式版本参数作为隔离测试入口；正式镜像和生产更新不得使用 `v26.9.9` 等测试候选版本。
- 本次没有删除或迁移数据库、用户、证书、端口、`.env` 或 Docker 数据卷；镜像尚未由本地变更直接宣称发布。

## 文档补充（2026-09-30，未发布）

- 补齐 `MR_SHAW_API_AND_RELEASE.md` 中原版 `.env.example` 的配置项说明，包括客户端模板、状态/自动清理、通知/Webhook、JWT、调度间隔和开发开关。
- 明确截图中的“变量/描述”表是运行配置，不是 HTTP API；原版 API 以启用 `DOCS=True` 后的 `/docs`、`/redoc` 和源码路由为准。
- 记录底部捐赠菜单的真实修改位置：`app/dashboard/src/constants/Project.ts` 的 `DONATION_URL` 控制跳转，README 中英文本的 `Donation/捐赠` 小节控制钱包地址展示；本次没有修改捐赠地址、支付逻辑、数据库、Node 通道或生产配置。

## mrshaw-v0.8.4-preview.4（2026-09-30，已发布）

- 根据服务器截图将节点设置弹窗最大宽度由 860px 收窄为 800px，原有左右对称内边距及手机端视口规则保留。
- 将运行指标的“刷新”按钮从最右端移到标题旁边，保留手动刷新和 15 秒自动刷新。五项指标铺满收窄后的可用内容区，不再因 700px 上限在右侧留出额外空白。
- 原版 Chakra 主题、证书、端口、使用系数、启用开关、保存、删除、住宅出口和五项运行指标均保留；API、数据库、Node 通道及部署配置无变化。
- 仅修改原有布局属性，不新增覆盖 CSS；本机使用真实组件和原 Chakra 主题完成桌面/手机响应式渲染验收。Actions `36726339140` 已成功发布多架构镜像；服务器截图仍需由部署环境完成验收。

## mrshaw-v0.8.4-preview.3（2026-09-30，服务器验收预览版）

- 按生产截图将节点设置弹窗最大宽度从 1040px 收窄为 860px，桌面横向内边距调整为 20–24px；节点运行指标区域从 820px 收窄为 700px。直接修改现有 Chakra 布局属性，不追加覆盖样式。
- 保留五项运行指标、原版 Chakra 主题、证书、端口、使用系数、启用开关、保存、删除和住宅出口管理；手机端仍按视口宽度收缩。
- API、数据库、Node 通道及部署配置均无变更，无需更新 Marzban-Node。先由 Actions 构建并核对 GHCR revision，再用于服务器验收，不标记为稳定版。

## mrshaw-v0.8.4-preview.2（2026-09-30，服务器验收预览版）

- 节点弹窗最大宽度由 1360px 改为 1040px，保持手机端视口内宽度；修正节点运行指标的布局，五张卡片从蓝色区块左侧开始排列、最大宽度 820px，中等宽度自动换行。原有证书、端口、节点表单和住宅出口管理不变。
- 新增 `MR_SHAW_API_AND_RELEASE.md`，明确环境变量、受保护 API、Node 内部通道及每次更新的文档/测试/镜像发布流程。本次没有改变任何 API 请求或响应。
- 本地 TypeScript/Vite 构建、17 项后端单元测试和差异空白检查通过。此次仅调整前端及文档，没有 API、数据库结构或 Node 通道变更；无需更新 Node。
- 配对 Node 基线：`kissow/Marzban-node` 的 `3e9b92e590a1c3c81af59b08d620f4a6209f2b71`。主面板镜像以本次合并提交及成功 Actions 的 OCI revision/digest 为准，不把构建排队当作发布成功。
- 用户要求先构建并在现有服务器验收本次布局；桌面/手机实际截图尚待服务器反馈，不标记为稳定版。已有部署使用 Fork 的 `marzban update`，先确认自动备份成功，保留数据库、用户、证书、端口、`.env` 和住宅代理配置。

## mrshaw-v0.8.4-preview.1（2026-09-30，预览版）

- 节点设置弹窗改为最大约 1360px 的响应式宽版，保留原有证书、端口、启用开关、保存和删除等官方 Chakra 界面功能。
- 节点运行状态显示 CPU、内存、磁盘、运行时间、活跃用户五项；宽屏五列、手机端两列。没有可靠节点级来源时，活跃用户显示不可用，不虚构数量。
- 本地前端构建已通过；真实 Linux Node、Xray 和测试数据库迁移仍需验收，暂不建议直接用于生产环境。

## 开发中（尚未稳定发布）

- 节点设置沿用官方 Chakra 界面与证书、端口、启用开关等原功能，新增按节点折叠展示的运行状态。
- 新增受管理员权限保护的 `GET /api/node/{node_id}/health`，通过原有认证通道读取该节点的 CPU、内存、磁盘、运行时间；无可靠来源的在线设备数返回空值。
- 每个 Marzban-Node 可独立保存一条 HTTP 或 SOCKS5 住宅 IP 出口。支持服务器、端口、可选账号密码；密码加密存储，API 不回显明文。
- 保存出口时只向对应 Node 下发配置，旧版 Node 不支持扩展时拒绝保存；删除出口后恢复原有路由。
- （历史阶段记录）设备数量限制当时尚未实现，计划在用户设置区域单独开发；该阶段已被上方的用户设备登记、独立凭据和 Node 配置加载链取代，不能把公网 IP 数当作实际设备数。

发布时须记录与 `kissow/Marzban-node` 的配对版本，并完成真实 Xray、Linux Node 与数据迁移测试。
