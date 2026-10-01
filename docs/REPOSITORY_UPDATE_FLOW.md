# Mr.shaw Fork 更新、接口与验收登记

本文把本 Fork 每次更新必须同步的流程、接口登记和本次变更证据放在仓库内，避免依赖工作区外的资料文件。它适用于 `kissow/Marzban`；如果一次变更同时涉及 `kissow/Marzban-node` 或 `kissow/Marzban-scripts`，三个仓库必须记录配对 commit 和兼容性。

## 1. 每次更新必须同步的资料

1. `CHANGELOG.md`：用户可见变化、兼容性、已知限制和发布状态。
2. `README.md` / `FORK_FEATURES.md`：功能边界、安装/更新方式和与官方版本的差异。
3. `MR_SHAW_API_AND_RELEASE.md`：新增、修改、删除的 API、数据库、Node 通道和配置字段。
4. `RELEASE_CHECKLIST.md`：代码、迁移、构建、CI、镜像和服务器验收闸门。
5. 本文：跨仓库登记、接口索引、测试证据、源 commit、镜像摘要和服务器验收状态。

只改 UI 或文档也要明确记录：API、数据库、Node 通道、证书、端口和 Xray 核心无变化。未完成 CI、镜像或服务器验收时，状态只能写“测试中 / 未发布”，不能给生产服务器更新命令。

## 2. 当前变更登记卡

```text
变更编号：MR-20261001-DEVICE-LIMIT
日期：2026-10-01
标题：在官方 Chakra 用户结构中加入用户级 HWID 设备登记限制
状态：测试中 / 未发布

主面板：kissow/Marzban
Node：kissow/Marzban-node（无变化，不需要配对更新）
脚本：kissow/Marzban-scripts（无变化）
数据库迁移：4a9d2e8b7c61_add_user_device_limit.py
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

迁移 `4a9d2e8b7c61_add_user_device_limit.py` 新增用户字段、`user_devices` 表和 PostgreSQL 枚举。删除用户会级联清理设备记录；撤销设备后可以重新登记。回滚前必须备份数据库，禁止删除数据卷。

## 4. 已完成的本地证据

- `python -m compileall -q app`：通过。
- 完整后端测试：`python -m unittest discover -s tests -p 'test_*.py' -v`，目标为 `22 passed`。
- 设备限制专项测试：`5 passed`。
- 前端 TypeScript 检查和 `npm run build`：通过。
- Alembic：`4a9d2e8b7c61` 为唯一 head。
- SQLite upgrade/downgrade：通过。
- `git diff --check`：通过。

以下仍未完成，因此不能发布：PostgreSQL 真实迁移、Linux 隔离环境、并发锁验证、V2RayN/Clash/Hiddify/Shadowrocket 的真实 HWID 兼容矩阵、生产服务器验收，以及本次修复后的 GitHub Actions 和 GHCR 镜像发布。此前 Actions run `36832627106` 因专项测试误用未声明的 pytest 而失败，修复后的 run `36835708735` 又发现锁定 APScheduler 导入 `pkg_resources`、但新版 setuptools 已移除该模块；这两轮失败都必须保留在发布记录中，避免只依赖本地环境或误把“代码已推送”当成“镜像已发布”。当前已统一测试框架并在 `requirements.txt` 锁定 `setuptools<81`，下一轮必须用同一条 `unittest discover` 命令复验。

## 5. 发布顺序

1. 先更新代码、接口文档、CHANGELOG、README/FORK_FEATURES 和本登记卡。
2. 执行后端测试、前端构建、迁移升级/回滚和 `git diff --check`。
3. 在功能分支提交并推送；CI 成功后核对源 commit、镜像 tag、index/架构 digest 和 OCI revision。
4. 仅在镜像证据齐全后进入隔离服务器，先备份数据库、`.env`、证书、Xray 配置和数据卷。
5. 已切换 Fork 的安装使用 `marzban update`；官方旧安装首次切换使用 `marzban adopt`；新服务器才使用 `install`。
6. 服务器验收用户、订阅、节点、证书、端口、日志和手机/桌面页面后，才允许把状态改为稳定发布。

不得使用 `docker compose down -v`，不得覆盖 `.env`，不得删除 `/var/lib/marzban*`，不得把未发布代码直接覆盖正式 `latest`。

