# Marzban 主面板发布清单

本清单适用于 `kissow/Marzban` 的每一次代码、接口、数据库、管理端 UI、配置、Xray 核心或文档更新。它必须和仓库内的 [`docs/REPOSITORY_UPDATE_FLOW.md`](docs/REPOSITORY_UPDATE_FLOW.md) 一起使用；工作区中的 05/06/08/09 项目资料仍可作为扩展记录，但仓库内文档是上传后可复核的最小完整记录。

## 变更登记

- [ ] 已记录日期、标题、发布状态和主面板 commit。
- [ ] 已标记变更是否涉及 API、数据库迁移、Node 通道、订阅响应、证书、端口、`.env`、Xray 核心和 UI。
- [ ] 已确认主面板、Node、脚本是否需要配对发布；没有影响的仓库也写明“无变化”。
- [ ] 没有把 `_patch.tmp`、`ui-preview/`、构建临时目录、数据库、密钥或生产配置加入提交。

## 代码和接口

- [ ] 新增、修改或删除的路由已在 `MR_SHAW_API_AND_RELEASE.md` 登记：方法、完整路径、认证、请求、响应、错误码、副作用、Node 兼容、弃用和回滚。
- [ ] `.env.example`、配置表和 README 已同步；真实密码、Token、数据库连接串和代理凭据未进入仓库。
- [ ] 数据库变化有 Alembic 迁移、升级前备份、回滚测试和旧用户/节点数据验证。
- [ ] 只改 UI 或文案时明确写出：API、数据库、Node 通道、证书和端口无变化。
- [ ] 接口、订阅字段、Node 通道或配置字段变化已同步写入 [`docs/REPOSITORY_UPDATE_FLOW.md`](docs/REPOSITORY_UPDATE_FLOW.md)，并通知 Node/scripts 配对文档。

## 测试

- [ ] `python -B -m unittest discover -s tests -v`
- [ ] CI 使用的测试命令与本地测试命令一致；新增测试默认使用仓库现有 `unittest` 规范，未引入未声明的 pytest/fixture 依赖。
- [ ] 干净 CI 安装后导入所有测试模块；旧依赖若使用已移除的兼容模块（例如 `pkg_resources`），必须在依赖文件中显式锁定兼容版本。
- [ ] 单元测试导入数据库/应用模块时不隐式依赖 `/usr/local/bin/xray` 等生产服务；外部二进制依赖必须在测试步骤显式准备或由测试专用桩隔离。
- [ ] 管理端 `npm run typecheck` 和 `npm run build`
- [ ] `git diff --check`
- [ ] 订阅、二维码、用户到期、节点、证书和端口回归通过。
- [ ] Node 配对契约、健康状态、住宅出口（如适用）和失败回滚通过。
- [ ] 桌面和手机视口真实渲染通过；记录视口、缩放、截图和是否横向溢出。

## CI、镜像和发布

- [ ] GitHub Actions 成功，记录 workflow、run ID、源 commit 和失败重试结果。
- [ ] 如 Actions 失败，记录失败步骤、根因、修复提交和重新构建结果；失败状态不得写成镜像已发布。
- [ ] `ghcr.io/kissow/marzban` 的 tag/index digest、amd64/arm64 digest 与 OCI revision 对应源 commit。
- [ ] 镜像能在干净环境拉取并启动；没有把 Actions 排队或代码已推送误写成已发布。
- [ ] `CHANGELOG.md`、`FORK_FEATURES.md`、README、接口文档和项目验收清单状态一致。

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
