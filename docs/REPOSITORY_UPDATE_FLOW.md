# Mr.shaw Fork 更新、接口与验收登记

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

