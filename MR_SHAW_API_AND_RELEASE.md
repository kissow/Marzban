# Mr.shaw 扩展接口与更新规范

## MR-20261007-BROWSER-TRANSLATION（展示兼容，本地修复、未发布）

无接口、字段、认证、迁移、命令新增/删除。原 GET /api/hosts、PUT /api/hosts 及 GET /api/inbounds 的请求/响应/权限不变；只保护浏览器 DOM 和包装两个动态状态文本。Node REST/RPyC/HWID/UDP 与正式 Xray v26.3.27 不变；Node/scripts 不需配对更新。未来主控镜像发布后使用既有 marzban update；当前不能获得未发布代码。面板原语言菜单保留。[源码、测试和上线验收边界](docs/BROWSER_TRANSLATION.md)。

## MR-20261006-CONTROL-RESILIENCE（镜像已发布，服务器验收待完成）

不新增接口、字段、迁移或端口。原 `/api/nodes`、`/api/node/{node_id}` 的 status/message 和异步 `POST /api/node/{node_id}/reconnect` 合同保留，受理不等于连通；日志控制探测异常使用既有关闭码 4400。Node 认证通道不变：仅 `/`、`/ping`、`/health`、`/device-activity` 在网络异常后最多再读一次；改变状态的请求不立即重放。精确 403 Session mismatch 才清除 session。TLS 15s、REST 连接/读取各 10s、REST API 就绪 10s、健康统计 5s、失败退避 30s 均为阶段参数，非全流程硬期限。HWID/订阅合同和正式 Xray v26.3.27 不变。Node/scripts 无变化；新主控镜像已发布，既有 Fork 执行 `marzban update`。PR #12 / `eb43761e` / Actions `37486719383` 与双架构摘要已核对，服务器验收待执行。[完整接口合同、发布证据及上线验收](docs/NODE_CONTROL_RESILIENCE.md)。

## MR-DASHBOARD-I18N-MOBILE：展示层修复，接口不变（镜像已发布，服务器/视觉验收待完成）

`GET /api/users` status 查询仍用 `active/on_hold/disabled/limited/expired`，只翻译显示文案。`GET /api/hosts`、`PUT /api/hosts` 请求/响应/管理员权限及端口转换不变；必填提示只是前端本地化。无接口新增删除、认证变更或数据库迁移。Node REST/RPyC、健康/设备策略协议及部署命令不变，Node/scripts 不需本轮更新；Xray v26.3.27 不变。

本地/Linux CI 语言 34/34、主控 95/95、TypeScript/构建通过。PR #11 合入 `56552130`，Actions `37353281396` 成功，latest 双架构摘要和 OCI revision 已核对；已切换 Fork 的主控使用 `marzban update`，Node 不需更新。响应式源代码约束测试不是实际浏览器验收，服务器/视觉验收仍待完成。[完整发布证据](docs/DASHBOARD_I18N_MOBILE.md)。

## MR-20261006-NODE-RECOVERY：既有接口行为（镜像已发布，服务器验收待完成）

`GET /api/nodes` 与 `GET /api/node/{node_id}` 原 status/message/xray_version 返回合同不变，message 增加内部失败阶段。`POST /api/node/{node_id}/reconnect` 原 sudo-admin 权限/响应不变：200 仅表示异步任务接受，进行中的重复重连可合并，不等于连接成功。`PUT`/`DELETE /api/node/{node_id}` 内部与恢复使用同一节点锁；请求、响应、权限不变。

Node REST/RPyC 方法、认证、字段及健康/设备策略线协议不变；没有新端口、数据库迁移、UI/HWID/UDP/核心变化。已配对 Node/scripts 无需本轮更新；主控镜像已发布：源 `122632c8`、Actions `37340574125`、双架构 OCI revision 核对通过。本地两轮 95/95 与 Linux 95/95 通过，服务器部署/验收未执行。[镜像摘要、完整超时、兼容和验收边界](docs/NODE_RECOVERY_RELEASE.md)。

## MR-20261003-DONATION-LINK：Fork 捐赠入口

镜像发布状态：Actions 37123809995 成功，主面板 latest 的 amd64/arm64 revision 均为 e72943b6dad1abf6ccd58307cb1008bd6793d81f；digest 与服务器更新方式见发布记录。没有 API/协议变更或 Node 更新要求，服务器点击验收尚待确认。

只更改前端 `DONATION_URL` 和中英文 README 的捐赠说明，不是 API 或收款服务。API、数据库、Node 通道、订阅、认证、证书、端口、环境文件、数据卷及 Xray v26.3.27 均无变化；Node/scripts 无需配对构建或服务器更新。[发布记录](docs/DONATION_LINK_RELEASE.md)。

## MR-20261003-EGRESS-UDP：住宅出口合同扩展（镜像已发布，服务器验收待完成）

没有新增路径或认证：sudo 管理员的 `GET/PUT/DELETE /api/node/{node_id}/egress` 沿用原合同。PUT 新增 `udp_mode=legacy|proxy|tcp_only`（省略 legacy），GET 已配置时返回模式；密码仍不回显。HTTP+proxy 或非法模式 422；旧/离线/能力不足 Node 在保存前 409。非 legacy 需要 `managed-outbounds-v1` 和新增 `managed-outbounds-udp-v1`，重连时重复检查。成功写库只代表异步重启已排队，不代表供应商连通性通过。

认证 REST/RPyC 配置通道只添加可选 extension 字段；legacy 为兼容旧 Node 省略此字段。additive 迁移 `7e8f9012ab34` 只增加 `node_egress.udp_mode`，不改用户/节点/凭据。两运行时仓库需要配对发布，scripts/证书/端口/环境/数据卷/核心 v26.3.27 无变化。协议、DNS 替换和显式路由优先级、错误、弃用/回退及验收完整说明见 [NODE_EGRESS_UDP.md](docs/NODE_EGRESS_UDP.md)。当前配对 latest 已发布并核对源提交；真实服务器与供应商仍待验收。

发布证据（配对源 SHA、Actions、两镜像 index/架构 digest/OCI revision、scripts 文档提交）见 [EGRESS_UDP_RELEASE.md](docs/EGRESS_UDP_RELEASE.md)。服务器未验收，不是稳定版。

## 2026-10-03 订阅兼容合同（镜像已发布，服务器验收待完成）

沿用订阅 token 认证、原路径和参数，没有新增接口或迁移：

| 方法和路径 | 输入与结果 | 副作用和限制 |
| --- | --- | --- |
| `GET /{XRAY_SUBSCRIPTION_PATH}/{token}` | 无 `X-HWID`：正常订阅为 `200`，使用原共享凭据，不再因 `reject_new` 返回 `428` | 不新增设备记录；共享账号保留，无法强制执行 HWID 限额 |
| `GET /{XRAY_SUBSCRIPTION_PATH}/{token}/{client_type}` | sing-box/clash-meta/clash/outline/v2ray/v2ray-json 共用同一兼容逻辑 | User-Agent 自动识别路径同样兼容，原格式生成器未改 |
| 上述两个订阅路由，携带 `X-HWID` | `reject_new` 登记成功返回独立凭据；同 HWID 重用；新 HWID 超额 `429`；无有效登记凭据 `403`；空/过长 HWID 仍为 `400` | 0 不限制数量；成功登记后经现有通道同步共享与独立账号到主核心和在线 Node |

原鉴权、账号状态、到期与 token 错误行为保持不变；上表的 200 以原订阅有效为前提。无 HWID 或共享配置复制可以绕过 HWID 限额，因此不宣称全客户端或物理设备强制限制。`policy_enforcement` / `direct_connection_enforced` 原 ACK 字段不变，只表示合同/独立凭据支持，不证明所有客户端已被拦截。Node/scripts 运行时、UI、数据库 schema、证书、端口和 Xray `v26.3.27` 无变化；无需 Node 更新。回退使用更新前保存的镜像与配置；回退会重新带回旧版无 HWID 的订阅问题，不删除设备记录或数据卷。发布与服务器验收状态见发布清单。

发布证据：主面板源 commit `37bab0b113c44ccb2a9db6230ac982b7d2a889a1` / Actions `37090609233` / GHCR `latest` index `sha256:c4bbe88b5b547bbdca3d6b8a4bf1e7c92aeb29ae50b36cd758b7c6eccae2edfc`；配对 Node 源 commit `c135743d1ad26d45538e4c6c7a65a9c6693856a8` / Actions `37090612247` / GHCR `latest` index `sha256:21340918298f0b8647fb7eb360294334891fc219e280a75af5d133c66ee9fbc1`。镜像已经发布，服务器验收仍待完成。

## 2026-10-02 本地接口增补（未发布）

`GET /api/node/{node_id}/health` 增加 Node 活动来源、scope、采样窗口和时间，以及策略数量、revision、同步时间、同步状态与 `direct_connection_enforced=true`。优先保留 Node 原生在线用户，旧 Node 才使用面板近期用量回退。

Node 内部新增 `POST /device-activity`、`POST /device-policies` 及对应 RPyC 方法；沿用 TLS 认证通道和现有端口。设备数量上限在创建/修改用户 API 统一校验为 0–100000。本轮没有新增数据库迁移；策略确认只表示接收，`reject_new` 仍在带 HWID 的订阅请求时执行。

完整请求/响应、403/422、原子替换、重试、兼容与回退见 [Node 活动统计与设备策略合同](docs/NODE_ACTIVITY_AND_POLICY.md)。

本文说明本 Fork 新增的用户级订阅设备登记限制、节点健康与每 Node 住宅代理功能。原版全部接口仍以代码和运行实例的 OpenAPI 为准；`.env` 变量不是 API，不应把内部 Node 通道暴露给第三方项目。没有填写住宅代理主机、端口等参数时，不会自动生成住宅 IP。

跨主面板、Node、脚本的更新登记必须同时填写仓库内的 [`docs/REPOSITORY_UPDATE_FLOW.md`](docs/REPOSITORY_UPDATE_FLOW.md)，并按本仓库的 [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) 逐项检查。本文是主面板接口字段的维护源；三仓库的可依赖接口、Node 通道和脚本命令索引也在上述文档中。任何接口、订阅响应、Node 通道或配置字段的变化，都必须在同一个变更中更新本文、总索引、对应 CHANGELOG、README/FORK_FEATURES 和验收清单。

## 三层边界

1. **主面板配置层**：`/opt/marzban/.env` 设置运行环境，`/var/lib/marzban` 保存默认数据库、Xray 配置等数据；路径随实际部署而异。`SUDO_USERNAME`/`SUDO_PASSWORD` 用于初始化管理员，`SQLALCHEMY_DATABASE_URL` 指向数据库，`UVICORN_HOST`/`UVICORN_PORT` 指定 Web 监听，`XRAY_JSON` 指向 Xray 配置文件，`XRAY_EXECUTABLE_PATH` 指向二进制，`XRAY_SUBSCRIPTION_URL_PREFIX` 是订阅 URL 前缀，`DOCS=True` 才显示 `/docs` 和 `/redoc`。这些是进程配置项，不是 HTTP 路径；不要在文档或截图中泄露 `.env`、数据库连接串和密钥。升级不要覆盖已有 `.env`。
2. **主面板管理员 API**：统一在 `/api` 下；下列节点相关接口均要求现有超级管理员 Bearer Token，不应直接开放给用户端。认证入口为 `POST /api/admin/token`，按原版现有认证流程取令牌；不要把管理员凭据写到浏览器公开脚本或第三方仓库。
3. **Node 内部通道**：Marzban 通过原有认证连接向对应 Marzban-Node 取指标并下发配置。REST 模式下 Node 的 `POST /health` 需要有效 `session_id`；RPyC 模式使用 `fetch_health`。它们不是面向第三方的公开监控接口，不新增公网监控端口。Node 的 Xray API 端口与住宅代理商提供的端口也不是同一种端口。

## 原版环境变量、接口边界与捐赠入口

截图中 README 的“变量/描述”表不是 HTTP 接口，而是 Marzban 启动时读取的 `.env` 环境变量。完整默认示例以 [`.env.example`](.env.example) 为准；下面按功能说明，新增配置时必须同时更新 `.env.example` 和本文，不要把真实密码、Token、数据库连接串或钱包私钥提交到仓库。

| 配置项 | 作用 | 是否通常需要改动 |
| --- | --- | --- |
| `UVICORN_HOST` / `UVICORN_PORT` | Web/API 监听地址和端口 | 按部署端口改；反代场景通常保持默认监听 |
| `ALLOWED_ORIGINS` | 浏览器跨域来源白名单 | 有独立前端域名时按需填写 |
| `SUDO_USERNAME` / `SUDO_PASSWORD` | 初始化管理员信息 | 仅首次初始化使用，优先用 CLI 创建管理员 |
| `UVICORN_UDS` | Unix Socket 监听路径 | 只在 Nginx/本机 Socket 部署时使用 |
| `UVICORN_SSL_CERTFILE` / `UVICORN_SSL_KEYFILE` / `UVICORN_SSL_CA_TYPE` | 应用自身 HTTPS 证书、密钥和 CA 类型 | 已由反向代理终止 HTTPS 时通常不填 |
| `DASHBOARD_PATH` | 管理面板路径前缀 | 需要非根路径部署时设置 |
| `SQLALCHEMY_DATABASE_URL` | SQLite、PostgreSQL、MySQL/MariaDB 数据库连接 | 迁移数据库时设置，升级不能覆盖 |
| `SQLALCHEMY_POOL_SIZE` / `SQLIALCHEMY_MAX_OVERFLOW` | 数据库连接池参数 | 高并发时按数据库容量调整 |
| `XRAY_JSON` | Xray JSON 配置文件路径 | 使用自定义配置时设置 |
| `XRAY_EXECUTABLE_PATH` / `XRAY_ASSETS_PATH` | Xray 二进制和 Geo 资源路径 | 自定义 Xray 安装路径时设置 |
| `XRAY_SUBSCRIPTION_URL_PREFIX` / `XRAY_SUBSCRIPTION_PATH` | 用户订阅 URL 的域名/前缀和路径 | 订阅域名或路径变化时设置 |
| `XRAY_EXCLUDE_INBOUND_TAGS` / `XRAY_FALLBACKS_INBOUND_TAG` | 排除入站标签、备用入站标签 | 使用备用/回落入站时设置 |
| `TELEGRAM_API_TOKEN` / `TELEGRAM_ADMIN_ID` / `TELEGRAM_LOGGER_CHANNEL_ID` | Telegram 机器人、管理员和日志频道 | 启用 Telegram 功能时填写 |
| `TELEGRAM_DEFAULT_VLESS_FLOW` / `TELEGRAM_PROXY_URL` | Telegram 默认 VLESS flow 和代理 | 按客户端/网络环境按需设置 |
| `DISCORD_WEBHOOK_URL` | Discord 通知 Webhook | 需要 Discord 通知时填写 |
| `CUSTOM_TEMPLATES_DIRECTORY` | 自定义订阅模板目录 | 使用自定义模板时设置 |
| `CLASH_SUBSCRIPTION_TEMPLATE` / `SUBSCRIPTION_PAGE_TEMPLATE` / `HOME_PAGE_TEMPLATE` | Clash、订阅页、首页模板 | 修改订阅或页面外观时设置 |
| `V2RAY_SUBSCRIPTION_TEMPLATE` / `V2RAY_SETTINGS_TEMPLATE` | V2Ray 订阅和设置模板 | 使用自定义 V2Ray 输出时设置 |
| `SINGBOX_SUBSCRIPTION_TEMPLATE` / `SINGBOX_SETTINGS_TEMPLATE` | Sing-box 订阅和设置模板 | 使用自定义 Sing-box 输出时设置 |
| `CLASH_SETTINGS_TEMPLATE` / `USER_AGENT_TEMPLATE` / `GRPC_USER_AGENT_TEMPLATE` | Clash settings and normal/gRPC User-Agent templates | Optional; change only when client output requires it |
| `MUX_TEMPLATE` | Mux 配置模板 | 需要自定义 Mux 时设置 |
| `USE_CUSTOM_JSON_DEFAULT` / `USE_CUSTOM_JSON_FOR_V2RAYN` / `USE_CUSTOM_JSON_FOR_V2RAYNG` / `USE_CUSTOM_JSON_FOR_STREISAND` / `USE_CUSTOM_JSON_FOR_HAPP` | 是否为各客户端使用 JSON 配置 | 只有客户端需要 fragment/mux 等能力时启用 |
| `SUB_PROFILE_TITLE` / `SUB_SUPPORT_URL` / `SUB_UPDATE_INTERVAL` | 订阅响应头中的标题、支持链接和更新间隔 | 按品牌和客户端需要设置 |
| `EXTERNAL_CONFIG` | 导入外部 V2Ray 配置 | 确认外部地址可信后使用 |
| `ACTIVE_STATUS_TEXT` / `EXPIRED_STATUS_TEXT` / `LIMITED_STATUS_TEXT` / `DISABLED_STATUS_TEXT` / `ONHOLD_STATUS_TEXT` | 自定义 Active、Expired、Limited、Disabled、On-Hold 文案 | 需要本地化或品牌文案时设置 |
| `USERS_AUTODELETE_DAYS` / `USER_AUTODELETE_INCLUDE_LIMITED_ACCOUNTS` | 过期用户自动删除策略 | 谨慎设置；负数表示关闭自动删除 |
| `NOTIFY_STATUS_CHANGE` / `NOTIFY_USER_CREATED` / `NOTIFY_USER_UPDATED` / `NOTIFY_USER_DELETED` / `NOTIFY_USER_DATA_USED_RESET` / `NOTIFY_USER_SUB_REVOKED` / `NOTIFY_IF_DATA_USAGE_PERCENT_REACHED` / `NOTIFY_IF_DAYS_LEFT_REACHED` / `NOTIFY_LOGIN` / `LOGIN_NOTIFY_WHITE_LIST` | 状态、登录、用量和用户变更通知 | 按通知策略设置 |
| `DOCS` / `DEBUG` | 开启 OpenAPI 文档、调试日志 | 仅开发/排错时临时开启 |
| `WEBHOOK_ADDRESS` / `WEBHOOK_SECRET` | 多 Webhook 地址和签名密钥 | 对接外部通知服务时设置 |
| `NOTIFY_DAYS_LEFT` / `NOTIFY_REACHED_USAGE_PERCENT` | 通知触发的剩余天数/用量百分比 | 按业务提醒策略设置 |
| `VITE_BASE_API` | 前端构建时使用的 API 基地址 | 前后端域名分离或反代路径变化时设置 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 管理员 JWT 有效期 | 按安全策略设置 |
| `JOB_CORE_HEALTH_CHECK_INTERVAL` / `JOB_RECORD_NODE_USAGES_INTERVAL` / `JOB_RECORD_USER_USAGES_INTERVAL` / `JOB_REVIEW_USERS_INTERVAL` / `JOB_SEND_NOTIFICATIONS_INTERVAL` | 核心、Node、用户用量、审核和通知任务间隔（秒） | 高负载时谨慎调整 |

Compatibility note: the current source reads the historical database-pool variable name `SQLIALCHEMY_MAX_OVERFLOW` (one `A` is missing). Do not replace it with the visually corrected `SQLALCHEMY_MAX_OVERFLOW` unless the code and migration notes are changed together. `RECURRENT_NOTIFICATIONS_TIMEOUT`, `NUMBER_OF_RECURRENT_NOTIFICATIONS`, and `DISABLE_RECORDING_NODE_USAGE` are also supported runtime variables and should be documented when they are enabled.

### 捐赠菜单到底改哪里

当前“捐赠”菜单不是收款接口，也不会调用任何外部收款服务。它由三处组成：

1. 菜单项和点击行为：[`app/dashboard/src/components/Header.tsx`](app/dashboard/src/components/Header.tsx) 的 `Link`、`header.donation` 和 `handleOnClose`。
2. 菜单跳转地址：[`app/dashboard/src/constants/Project.ts`](app/dashboard/src/constants/Project.ts) 的 `DONATION_URL`。当前值是 `https://github.com/kissow/Marzban#donation`，点击后打开本 Fork 的捐赠锚点。修改此常量后必须重新构建主面板镜像并更新服务器；只推送 README 不会替换已经运行的前端。
3. README 中展示的钱包地址：[`README.md`](README.md) 和 [`README-zh-cn.md`](README-zh-cn.md) 的 `Donation/捐赠` 小节。修改钱包地址时必须同时更新中英文 README，并核对网络名称，不能只改菜单 URL。

当前前端没有独立的捐赠管理页面，也没有捐赠订单、到账监控或二维码生成逻辑。若以后要接入数字货币收款，应作为独立支付功能开发，不能把钱包地址硬编码到管理端或用户端脚本中。

## 在 GitHub 仓库构建，服务器只拉取镜像

本 Fork 的生产镜像由仓库的 `.github/workflows/build.yml` 构建，不要求每次登录服务器编译。该工作流在 `master` 分支 push 或手动运行时执行后端单元测试、Dashboard TypeScript/Vite 构建，并发布多架构镜像 `ghcr.io/kissow/marzban:latest`；`docs/*`、`feature/*` 等普通分支不会覆盖生产 `latest`。

### 发布一次更新

1. 在本地完成功能、`CHANGELOG.md`、接口文档和验收记录，运行 `git diff --check`、后端测试和前端构建。
2. 推送到 Fork 的功能/文档分支，确认检查通过后合并到 `master`。不要直接把未验收的分支当作生产镜像。
3. 打开 GitHub 仓库的 **Actions → Mr.shaw fork image**，选择 `master`，点击 **Run workflow**；或者直接 push `master` 让它自动触发。
4. 等待 `verify-and-build` 全部成功，再检查该运行对应的 commit SHA 和 `ghcr.io/kissow/marzban:latest` 的发布时间/摘要。Actions 失败或 `latest` 尚未发布时，服务器不要更新。

### 服务器更新（仅拉取，不构建）

先进入服务器实际的 Marzban Compose 目录，确认 `docker-compose.yml` 使用的是 `ghcr.io/kissow/marzban:latest`，并备份 `.env` 与 `/var/lib/marzban`。然后执行：

```bash
cd /实际的/marzban目录
cp .env ".env.backup.$(date +%Y%m%d-%H%M%S)"
sudo tar -C /var/lib -czf "/root/marzban-data-backup-$(date +%Y%m%d-%H%M%S).tar.gz" marzban
docker compose pull marzban
docker compose up -d --no-build marzban
docker compose ps
docker compose logs --tail=100 marzban
```

只更新镜像和容器，不执行 `docker compose down -v`，不删除容器卷，不覆盖 `.env`、数据库、证书、端口、Xray 配置或 Node 配置。若部署不是 Compose，而是已安装的 `marzban` 管理脚本，则先执行 `sudo marzban status` 确认脚本版本，再按该脚本的 `update` 流程操作；两种部署方式不要混用。

### 更新后的验收顺序

先确认容器为 `Up`、迁移日志无错误，再登录管理面板检查管理员、用户、订阅、证书、端口和节点；最后逐台检查 Node、订阅导入和住宅出口。只有验收通过后，才在 `CHANGELOG.md` 把“未发布”条目标记为已发布，并记录实际 commit SHA、镜像摘要、备份文件和回滚方法。

## 本 Fork 节点 API 速查

2026-09-30 `mrshaw-v0.8.4-preview.4`（已发布）仅调整节点弹窗布局：最大宽度 800px，刷新按钮从最右端移至运行指标标题旁边，五项指标铺满可用内容区；API 请求、响应、权限和 Node 通道无变化，无需更新 Node。本机真实组件桌面/手机渲染已确认；Actions `36726339140` 成功，合并 SHA `ee96a1b8afe8fd638d75fe9b5975124268a02736`，`ghcr.io/kissow/marzban:latest` index 摘要 `sha256:e1ad34e5a0b4bd73811cc7d14f05b2f51641da80919a7b9224a0a4b469b58fdd`，amd64/arm64 revision 均匹配；服务器截图仍需在镜像发布后验收。

| 方法和路径（Marzban） | 用途与返回 | 写入/副作用 |
| --- | --- | --- |
| `GET /api/nodes` | 列出节点及 ID，供选择 `node_id`；原版接口 | 无 |
| `GET /api/node/settings` | 原版证书设置，节点安装时使用；不要删除或替换 | 无 |
| `GET /api/node/{node_id}/health` | 返回此 Node 的 `status`、`reason`、`metrics`，包含采样时间、CPU、内存、根目录磁盘、运行时间、数据来源；主面板可在 `metrics` 中补充最近 2 小时有正流量的去重用户及采样原因；离线或过期时 `metrics=null` | 通过已认证通道读取 Node，并查询主面板 `NodeUserUsage`；不写数据 |
| `GET /api/node/{node_id}/egress` | 返回 `configured`、协议、`udp_mode`、服务器、端口、用户名、`has_password`；**不返回密码** | 无；`udp_mode` 为本地未发布扩展 |
| `PUT /api/node/{node_id}/egress` | 保存该 Node 唯一的 HTTP/SOCKS5 代理。字段：`protocol`（`http`/`socks`）、`server`（代理商域名或 IP）、`port`（1–65535）、可选成对的 `username`/`password`、`udp_mode`（省略 legacy；proxy/tcp_only）。同用户名且密码留空可保留原密码 | 检查 `managed-outbounds-v1`；非 legacy 另检查 `managed-outbounds-udp-v1`；加密保存并异步重启。旧/离线/能力不足 409，参数或 HTTP+proxy 不合法 422；新模式本地未发布 |
| `DELETE /api/node/{node_id}/egress` | 清除该 Node 的代理设置 | 删除配置并异步重启该 Node，恢复原有默认路由 |
| `POST /api/node/{node_id}/reconnect` | 原版重连入口；排查离线 Node | 异步重连 |

Node 响应 `source=node-runtime` 与 `capabilities=["managed-outbounds-v1"]` 是扩展兼容性标记。主面板仅接受新鲜且合法的快照（超过 15 秒或异常则不展示为实时数据）。Node 原始快照没有可靠的在线用户来源时，`active_users` 为 `null`；主面板可根据最近 2 小时 `NodeUserUsage` 的正流量记录补充去重用户数，并返回 `active_users_window_hours`、`active_users_sampled_at` 和 `active_users_reason`。该值不是 Xray 实时在线连接数，不得用总在线数或 TCP 连接数填充。

节点管理弹窗在节点标题栏下方、证书区上方显示连接状态与原因：`node.message` 有值时优先显示后端原因，否则按 `connecting`、`error`、`disabled` 显示本地化兜底文案。`connecting` 和 `error` 状态提供“重新连接”按钮并调用上面的 `POST /api/node/{node_id}/reconnect`；`disabled` 只显示停用原因，不提供重连按钮。此项只改官方 Chakra UI 的原节点弹窗，不删除证书、端口、启用、保存或删除字段。

住宅代理地址从代理服务商取得，不填 Marzban 主面板地址、Node 地址、Node 的服务端口或 Xray API 端口。legacy 下 HTTP 只接管默认 TCP、UDP 按原路由；未发布新模式的 DNS 上游替换、显式路由优先级及其他 UDP 阻断边界见上方合同。保存操作只是排队重启，HTTP 成功**不等于**住宅代理可连通：还要复查 Node 运行日志、出站公网 IP 和原订阅可用性。本功能尚无代理失效自动摘除和自动回滚。

## 每次更新必须执行的流程

适用于主面板、Node、安装脚本、UI 和 API；即使只修布局，也要说明“接口无变化”。

1. **确定基线**：记录本次主面板/Node/脚本提交 SHA、当前镜像摘要、影响范围和原有数据路径。保护 `.env`、数据库、证书、端口、Xray 配置和用户记录；不在旧样式后叠加补丁，应修改原规则。预览稿必须和实际 Chakra 组件使用同一宽度/断点；截图验收要记录浏览器缩放与视口大小。
2. **写更新说明**：在对应仓库 `CHANGELOG.md` 的“未发布”条目写清改动、用户可见差异、兼容性及回退风险；不要把尚未打包的提交写成已发布版本。跨主面板和 Node 的功能，两边均要记录配对版本或 SHA。
3. **核对接口清单**：新增/修改/删除 API 时同步更新本文，逐项写 HTTP 方法、路径、权限、请求、响应、错误码、副作用、Node 通道和兼容约束。仅改 UI 时明确写“API 无变更”。更改配置项则同步更新配置表、示例与迁移说明；绝不提交真实密钥。
4. **测试并记录证据**：后端单测、前端 TypeScript/Vite、Node 单测/Xray 配置预检、迁移升级/回滚；检查旧用户、证书、端口、订阅和节点连接。真机桌面与窄屏逐项核对；出现问题先修再重测，更新 `05-检测测试验收清单.md` 的结果和剩余风险。
5. **先测试后发布**：先在隔离环境测试升级。CI 成功后核对镜像确实对应预期 SHA（不能只看仓库代码已提交），再公布可执行的服务器更新命令。`latest` 未发布成功时不得让服务器提前更新。Node/主面板协议变化需配对发布并按兼容顺序升级。
6. **部署与验收**：已有安装使用 `adopt`（首次从官方切 Fork）或 `update`（已在 Fork）；新机才用 `install`。先备份并核验，再更新主面板、逐台 Node，最后检查容器、日志、用户、订阅、节点、出站及桌面/手机端。不要用 `down -v` 或覆盖数据目录。正式发布记录写入两边实际提交 SHA、镜像摘要、测试结果和已知限制。

发布检查：代码、`CHANGELOG.md`、本文接口表、相应 README/FORK_FEATURES、验收清单必须一起审查；任一项缺失不发布镜像/更新指令。仅改文档也要说明其对应代码版本，不能把尚未实现的功能写成可用。

## 接口变更登记模板（强制）

新增、修改或删除 HTTP、WebSocket、订阅响应、Node 内部 REST/RPyC 方法或配置字段时，在本文件对应接口表旁补充以下信息，并在变更登记卡中引用代码 commit 和测试证据：

```text
方法和完整路径/方法名：
认证与权限边界：
请求字段、类型、必填性、默认值和敏感字段：
成功响应状态、字段和脱敏规则：
错误状态码、错误体和触发条件：
数据库、缓存、队列、异步重启等副作用：
Node 通道、能力标识、最低配对版本和旧 Node 行为：
订阅/客户端兼容范围：
弃用周期、替代路径和回滚方案：
契约测试、权限测试、迁移测试和隔离/真实环境证据：
```

删除接口不能只删除路由：必须记录旧客户端的错误行为、替代路径、数据迁移和恢复方法。只改 UI 或文案时，也要明确写出 `API、数据库、Node 通道、证书和端口无变化`，避免把 UI 变化误当成接口发布。
## MR-20261003-NODE-CONNECT / SCHEDULER-DEPENDENCY 接口登记

本轮不新增或修改公开 API 路径、权限、请求/响应字段和数据库 schema。
既有 `POST /api/node/{node_id}/reconnect` 仍异步执行；主控先建立 Node 认证会话，
再执行非 legacy 出口健康/能力检查和启动；失败原因仍使用节点原有 `message`。
Node REST/RPyC 线协议不变，已配对 Node/scripts 不需本轮更新，Xray v26.3.27 不变。
APScheduler 锁定 3.11.3；仅主控依赖变化。[合同、测试和发布记录](docs/NODE_CONNECTION_RELEASE.md)。
