# Mr.shaw 扩展接口与更新规范

本文只说明本 Fork 新增的节点健康与每 Node 住宅代理功能。原版全部接口仍以代码和运行实例的 OpenAPI 为准；`.env` 变量不是 API，不应把内部 Node 通道暴露给第三方项目。没有填写住宅代理主机、端口等参数时，不会自动生成住宅 IP。

## 三层边界

1. **主面板配置层**：`/opt/marzban/.env` 设置运行环境，`/var/lib/marzban` 保存默认数据库、Xray 配置等数据；路径随实际部署而异。`SUDO_USERNAME`/`SUDO_PASSWORD` 用于初始化管理员，`SQLALCHEMY_DATABASE_URL` 指向数据库，`UVICORN_HOST`/`UVICORN_PORT` 指定 Web 监听，`XRAY_JSON` 指向 Xray 配置文件，`XRAY_EXECUTABLE_PATH` 指向二进制，`XRAY_SUBSCRIPTION_URL_PREFIX` 是订阅 URL 前缀，`DOCS=True` 才显示 `/docs` 和 `/redoc`。这些是进程配置项，不是 HTTP 路径；不要在文档或截图中泄露 `.env`、数据库连接串和密钥。升级不要覆盖已有 `.env`。
2. **主面板管理员 API**：统一在 `/api` 下；下列节点相关接口均要求现有超级管理员 Bearer Token，不应直接开放给用户端。认证入口为 `POST /api/admin/token`，按原版现有认证流程取令牌；不要把管理员凭据写到浏览器公开脚本或第三方仓库。
3. **Node 内部通道**：Marzban 通过原有认证连接向对应 Marzban-Node 取指标并下发配置。REST 模式下 Node 的 `POST /health` 需要有效 `session_id`；RPyC 模式使用 `fetch_health`。它们不是面向第三方的公开监控接口，不新增公网监控端口。Node 的 Xray API 端口与住宅代理商提供的端口也不是同一种端口。

## 本 Fork 节点 API 速查

2026-09-30 `mrshaw-v0.8.4-preview.4`（用户已确认，待 CI 发布）仅调整节点弹窗布局：最大宽度 800px，刷新按钮从最右端移至运行指标标题旁边，五项指标铺满可用内容区；API 请求、响应、权限和 Node 通道无变化，无需更新 Node。本机真实组件桌面/手机渲染已确认；构建和镜像发布状态以对应 Actions 证据为准，服务器截图仍需在镜像发布后验收。

| 方法和路径（Marzban） | 用途与返回 | 写入/副作用 |
| --- | --- | --- |
| `GET /api/nodes` | 列出节点及 ID，供选择 `node_id`；原版接口 | 无 |
| `GET /api/node/settings` | 原版证书设置，节点安装时使用；不要删除或替换 | 无 |
| `GET /api/node/{node_id}/health` | 返回此 Node 的 `status`、`reason`、`metrics`，包含采样时间、CPU、内存、根目录磁盘、运行时间、数据来源；离线或过期时 `metrics=null` | 通过已认证通道读取 Node；不写数据 |
| `GET /api/node/{node_id}/egress` | 返回 `configured`、协议、服务器、端口、用户名、`has_password`；**不返回密码** | 无 |
| `PUT /api/node/{node_id}/egress` | 保存该 Node 唯一的 HTTP/SOCKS5 代理。请求字段：`protocol`（`http`/`socks`）、`server`（代理商域名或 IP）、`port`（1–65535）、可选成对的 `username`/`password`。同用户名且密码留空可保留原密码 | 检查 Node 是否声明 `managed-outbounds-v1`；加密保存密码并异步重启该 Node。旧 Node 不支持时返回 409，参数不合法返回 422 |
| `DELETE /api/node/{node_id}/egress` | 清除该 Node 的代理设置 | 删除配置并异步重启该 Node，恢复原有默认路由 |
| `POST /api/node/{node_id}/reconnect` | 原版重连入口；排查离线 Node | 异步重连 |

Node 响应 `source=node-runtime` 与 `capabilities=["managed-outbounds-v1"]` 是扩展兼容性标记。主面板仅接受新鲜且合法的快照（超过 15 秒或异常则不展示为实时数据）；`active_users` 当前没有可靠节点级来源，返回 `null`，页面显示“未提供节点级连接数据”。不要把总在线数或 TCP 连接数填充进去。

住宅代理地址从代理服务商取得，不填 Marzban 主面板地址、Node 地址、Node 的服务端口或 Xray API 端口。HTTP 代理只接管默认 TCP；UDP 仍按原路由。保存操作只是排队重启，HTTP 成功**不等于**住宅代理可连通：还要复查 Node 运行日志、出站公网 IP 和原订阅可用性。本功能尚无代理失效自动摘除和自动回滚。

## 每次更新必须执行的流程

适用于主面板、Node、安装脚本、UI 和 API；即使只修布局，也要说明“接口无变化”。

1. **确定基线**：记录本次主面板/Node/脚本提交 SHA、当前镜像摘要、影响范围和原有数据路径。保护 `.env`、数据库、证书、端口、Xray 配置和用户记录；不在旧样式后叠加补丁，应修改原规则。预览稿必须和实际 Chakra 组件使用同一宽度/断点；截图验收要记录浏览器缩放与视口大小。
2. **写更新说明**：在对应仓库 `CHANGELOG.md` 的“未发布”条目写清改动、用户可见差异、兼容性及回退风险；不要把尚未打包的提交写成已发布版本。跨主面板和 Node 的功能，两边均要记录配对版本或 SHA。
3. **核对接口清单**：新增/修改/删除 API 时同步更新本文，逐项写 HTTP 方法、路径、权限、请求、响应、错误码、副作用、Node 通道和兼容约束。仅改 UI 时明确写“API 无变更”。更改配置项则同步更新配置表、示例与迁移说明；绝不提交真实密钥。
4. **测试并记录证据**：后端单测、前端 TypeScript/Vite、Node 单测/Xray 配置预检、迁移升级/回滚；检查旧用户、证书、端口、订阅和节点连接。真机桌面与窄屏逐项核对；出现问题先修再重测，更新 `05-检测测试验收清单.md` 的结果和剩余风险。
5. **先测试后发布**：先在隔离环境测试升级。CI 成功后核对镜像确实对应预期 SHA（不能只看仓库代码已提交），再公布可执行的服务器更新命令。`latest` 未发布成功时不得让服务器提前更新。Node/主面板协议变化需配对发布并按兼容顺序升级。
6. **部署与验收**：已有安装使用 `adopt`（首次从官方切 Fork）或 `update`（已在 Fork）；新机才用 `install`。先备份并核验，再更新主面板、逐台 Node，最后检查容器、日志、用户、订阅、节点、出站及桌面/手机端。不要用 `down -v` 或覆盖数据目录。正式发布记录写入两边实际提交 SHA、镜像摘要、测试结果和已知限制。

发布检查：代码、`CHANGELOG.md`、本文接口表、相应 README/FORK_FEATURES、验收清单必须一起审查；任一项缺失不发布镜像/更新指令。仅改文档也要说明其对应代码版本，不能把尚未实现的功能写成可用。
