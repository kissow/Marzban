# Mr.shaw Marzban Fork 更新记录

本文件仅记录本 Fork 相对 [Gozargah/Marzban](https://github.com/Gozargah/Marzban) 的改动。原作者、许可证和上游 Git 历史均保留；完整功能边界见 [FORK_FEATURES.md](FORK_FEATURES.md)。

## 未发布：用户级设备登记限制（2026-10-01）

- 在保留官方 Chakra UI、证书、端口、Node 通道、支付和原有用户数据的前提下，在用户创建/编辑窗口的流量字段右侧加入“限制设备”。
- 新增 `users.device_limit`、`device_limit_mode`、`device_limit_action` 与 `user_devices` 表；迁移为 `4a9d2e8b7c61_add_user_device_limit.py`。
- 订阅请求可选携带 `X-HWID`、`X-Device-OS`、`X-Device-Model`；原始 HWID 只保存 SHA-256 哈希。同一 HWID 换公网 IP 不重复计数，同一公网 IP 下不同 HWID 分别计数。
- 新增 `/{XRAY_SUBSCRIPTION_PATH}/{token}/device-status` 脱敏统计；`reject_new` 超限返回 `429`，`log_only` 超限继续放行；普通订阅和显式客户端格式不能通过切换格式绕过登记。
- 不带 `X-HWID` 的旧客户端保持原订阅行为；该功能限制订阅请求登记，不是 Xray 实时连接数，也不能断开已导入配置。
- 本次没有修改 Marzban-Node、Xray `v26.3.27`、证书、端口、支付或住宅出口通道。后端 `unittest discover`（22 passed）、设备限制专项测试（5 passed）、前端 TypeScript/Vite 构建和 SQLite 迁移升级/回滚均已通过；PostgreSQL、真实客户端、Linux 联调和生产验收仍待完成，因此未发布镜像和服务器更新指令。

## CI 构建失败复盘（2026-10-01，已修复代码，待重新构建）

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
- 设备数量限制尚未实现，计划在用户设置区域单独开发，不能把公网 IP 数当作实际设备数。

发布时须记录与 `kissow/Marzban-node` 的配对版本，并完成真实 Xray、Linux Node 与数据迁移测试。
