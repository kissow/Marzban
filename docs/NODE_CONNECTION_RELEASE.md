# Node 初连与 APScheduler 依赖维护

编号：MR-20261003-NODE-CONNECT / MR-20261003-SCHEDULER-DEPENDENCY。
日期：2026-10-03。维护者：Mr.shaw。状态：本地回归通过，待提交/发布本轮镜像；服务器验收待完成。

## 根因与修复

住宅出口为 `tcp_only` 或 `proxy` 时，主控在 `node.connected=False` 状态先调用
`get_health()` 检查能力。健康读取使用现有认证会话，因而得到 `Node is not connected`，
尚未进入原本负责连接的 `start()`。这不是证书、端口或设备限制参数被改动。

`app/xray/operations.py::connect_node()` 现在先用既有 `node.connect()` 建立会话，
然后读取出口/健康、检查能力，再调用 `start()`。已连接会话复用；legacy 或无出口不额外
读取健康。连接失败仍写入原节点状态字段 `message`，日志追加异常原因。
原版重连 API 和 UI 不变，不新增监控端口。失败后 `_connecting_nodes` 清理，允许再次重试。

## 调度器依赖

旧 `APScheduler==3.9.1.post1` 导入 `pkg_resources`，触发 setuptools 弃用提示，
并曾在干净 CI 中因该模块缺失而失败。升级并固定 `APScheduler==3.11.3`，
该版本改用 `importlib.metadata`，移除仅为旧依赖设置的 `setuptools<81` 上限和
Docker 单独安装 setuptools 的步骤。不使用警告过滤来掩盖旧接口。

保留原 BackgroundScheduler、UTC、interval、coalesce、max_instances、启动/退出调用。
本项目调度任务使用内存 job store；本次不修改用户数据库或迁移任务存储。
SQLAlchemy 的 naive UTC 和 Pydantic `.json()` 弃用提示另行登记，不混入本次修复。

参考：APScheduler 原项目 https://github.com/agronholm/apscheduler 与
https://apscheduler.readthedocs.io/en/3.x/versionhistory.html （3.10.2 已替换旧导入）。使用其发行依赖，
未复制修改调度器源码；保留 Marzban、Marzban-Node、Xray 上游署名和许可证。

## 接口与配对范围

| 项目 | 本轮状态 |
| --- | --- |
| `POST /api/node/{node_id}/reconnect` | 原接口；仍异步调用 connect_node |
| `GET /api/node/{node_id}/health` | 路径/权限/字段不变；初连先建立会话 |
| Node `/connect`、健康读取、`/start` 与 RPyC | 无新增字段/方法；复用原认证通道 |
| 主控 `kissow/Marzban` | 需构建、发布并更新主控镜像 |
| Node `kissow/Marzban-node` | 无代码或线协议变化；已部署配对 UDP 功能的 Node 不需再次更新 |
| scripts `kissow/Marzban-scripts` | 无安装/更新命令或运行时变化；不需重建 |
| Xray | 固定正式基线 v26.3.27 不变 |

此处“Node 不需更新”不表示官方旧 Node 支持新增 UDP 模式：非 legacy 仍要求已有的
`managed-outbounds-udp-v1` 能力；不支持的 Node 仍明确拒绝该配置。
用户/节点/数据库、订阅/HWID 策略、`.env`、证书、端口与挂载数据不改动。

## 本地验证和发布证据

- 升级后现有 63 项与新增 6 项调度器测试：最终全量 69/69 通过（项目内 Python 3.12.14 / APScheduler 3.11.3）。
- 6 项调度器测试覆盖无旧依赖导入、UTC/defaults、decorator、naive UTC start_date、真实 interval 执行/退出与 job controls；子进程将 UserWarning 视为错误验证旧导入已消除。
- 新增 9 项连接编排回归覆盖连接顺序、legacy/无出口、会话复用、能力/认证/健康/API 失败、重试清理。
- TypeScript `tsc --noEmit` 与 Vite 生产构建通过；仍有既有的大 chunk 提示，不是构建失败。产物仅在项目 `.cache/verification/node-connect-dashboard`。
- `pip check` 无依赖冲突，`git diff --check` 通过（修复文档末尾空行后）；未屏蔽运行时弃用提示。
- 本地验证不代替干净 Linux Actions、双架构镜像及服务器验收；不复用上一次镜像摘要。
- 新源 SHA、Actions run、GHCR index/amd64/arm64 digest 与 OCI revision：待本轮提交/构建。

## 服务器验收与回退

仅在本轮镜像成功发布后，对已切换 Fork 的主控使用原 `marzban update`、`marzban status`。
更新前备份数据库、`.env`、证书、Xray 配置和挂载数据；不 reinstall、不删除卷。
保留更新前实际镜像摘要供回退，不将历史文档的摘要当作本机备份。

使用隔离用户/节点分别验证 tcp_only/proxy、重新连接、原端口 TLS/API、订阅与应用访问；
记录具体失败 message。legacy 与无出口连接也要回归，不能用本地 mock 测试代替真实网络验收。
