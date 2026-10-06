# MR-20261006-CONTROL-RESILIENCE：慢链路与会话恢复

状态：2026-10-06 修复已推送并经 PR #12 合入 master，正式 Linux Actions 成功，新镜像 latest 双架构摘要/OCI revision 已核对；服务器部署和真实网络验收待用户执行。下方测试不能作为线上连接已稳定的证明。

2026-10-06 按用户授权推送线上仓库、构建新镜像并提供 SSH 更新命令。下方登记本轮源提交、PR、Actions 和 GHCR 证据；仅文档回写使用 `[skip ci]`，不重建已核对的运行时镜像。服务器仍由用户更新并验收，不沿用旧发布证据。

## 1. 问题与已核对的原因

用户日志显示控制 TLS 握手、REST 读取和 Xray API 请求间歇超时。TCP 可连接及控制/API 端口正在监听，不代表 TLS、认证会话和 API 均已可用。相同目标先超时后成功，不能据此认定域名损坏或直接 IP 永久解决问题。

源码确认了一个放大故障的路径：Node 的既有 `/connect` 会创建新会话；若之前已连接，会停止正在运行的核心。主控原先把短暂 `/ping` 超时当作会话消失，可能进入重新建会话路径；健康检查异常还会请求重启核心。网络延迟因此可能变成实际用户中断。本轮不声称已经查明所有网络超时的物理原因，也不把控制通道故障归因于 HWID 策略。

## 2. 本轮改动

- REST 短暂读取失败保留现有 session。只有 `/ping` 明确返回 HTTP 403 且 detail 为 `Session ID mismatch.` 才清除会话并允许重新建立；其它认证失败不被当作可以跳过的失效会话。
- `connect()` 对现有会话严格复核。复核超时会抛出原因，不调用具有接管副作用的 `/connect`。RPyC ping 的 TimeoutError 同样不主动关闭已有传输；EOF 等确定失联路径保留原行为。
- TLS 证书获取改为 15 秒阶段期限；REST 默认连接/读取期限分别为 10 秒；REST API 就绪等待为 10 秒，健康统计 API 为 5 秒。
- 只有确认只读的 POST 路径 `/`、`/ping`、`/health`、`/device-activity` 可在网络 Timeout/ConnectionError 后立即重试一次。TLS 验证错误、非法 JSON、不成功 HTTP 响应不自动重试。
- `/connect`、`/disconnect`、`/start`、`/restart`、`/stop`、`/device-policies` 不在响应超时后立即重发。远端可能已经执行，不能当作安全只读请求处理。`/start`、`/restart` 仍使用明确的 10 秒请求期限。
- `/start` 返回既有 `Xray is started already` 时检查 API 就绪，不借此重启核心。管理员明确配置变更仍经既有 `/restart` 应用，不取消正式重启功能。
- 不确定的控制/API 健康检查错误保留原因，30 秒退避后复查，不盲目重启；确认会话缺失或核心停止才走连接/启动恢复路径。API 迟到就绪可以清除旧错误状态。
- 健康探测最多 10 路并行，按完成顺序处理；每节点生命周期锁仍保护恢复操作。一个慢节点不阻止另一个已完成探测节点进入恢复。
- 批量设备账号同步每批只获取一次目标快照，不为每个用户、每个入站重复探测所有 Node；重叠批次合并，单用户/节点异常隔离，下次周期补偿。流量采集及日志入口也隔离控制探测异常。

这些期限是单阶段或无数据读取期限，不是全流程硬截止时间：DNS、多地址尝试、多次探测及持续分块响应可能增加总耗时。本轮没有给 Node `/connect` 增加服务器端幂等键；初次建会话超时且未拿到 session ID 时，远端结果仍不确定，后续恢复可能需要重新建会话。

## 3. 接口、协议和三仓库兼容

| 范围 | 合同与本轮影响 |
| --- | --- |
| 主控 `GET /api/nodes`、`GET /api/node/{node_id}` | 原 status/message/xray_version 合同不变；失败原因继续通过原字段返回 |
| 主控 `POST /api/node/{node_id}/reconnect` | 原管理员认证、异步恢复和每节点锁不变；HTTP 200 只表示请求已受理，不能证明节点已连通 |
| 主控 Node 日志 WebSocket | 保留原入口/认证；控制探测异常返回已有关闭码 4400 与原因，不泄漏未处理异常 |
| Node `/connect`、`/ping`、`/start` 等认证通道 | 不新增路径/字段，不改变端口、证书校验与 mTLS；仅主控的使用方式、读取重试和期限调整 |
| 设备策略、账号、订阅 | 字段、HWID 范围及 reject_new/log_only 含义不变；同步优化不是新增物理设备或实时在线拦截能力 |
| 数据库、UI、部署 | 无迁移、无主题/布局修改、无安装脚本变化；保留用户、数据库、.env、配置、证书和挂载数据 |
| Marzban-node / Marzban-scripts | 本轮运行时代码、接口与命令无变化，不需为本修复单独更新或构建 |
| Xray | 正式基线仍为 v26.3.27；本轮不升级或更换核心 |

本轮已发布的新主控镜像包含本修复；历史镜像 revision、Actions 和 digest 均不是本轮的发布证据。源码依据来自本项目及上游保留的 Node 会话语义，本轮没有复制第三方新代码。

## 4. 本地检测证据（2026-10-06）

固定 PowerShell 7、项目内 Python 3.12 测试环境和项目内缓存；命令统一使用 `Invoke-ProjectTools.ps1`。

- 最终同一运行时代码完整 unittest **连续两轮 116/116**，退出码均为 0。
- `test_node_control_resilience.py` **20/20 连续三轮**：只读重试、变更请求不重放、保留会话、精确 403、认证错误、API 退避/迟到恢复、100 用户单快照、批次锁、多节点并行、流量和日志异常隔离。
- `test_node_recovery.py` **13/13 连续三轮**：真实延迟 TLS、TLS 超时、mTLS 证书拒绝、新旧 RPyC 服务、生命周期/管理路由及恢复隔离。延迟/超时场景使用本地套接字和缩短的测试期限，不冒充生产网络 15 秒实测。
- 设备策略与连接编排专项 30/30；compileall、pip check、固定入口 Check/diff 检查通过。
- 复核修正了流量异常分支缺少 logger 导入，新增生产导入与日志路由异常测试；测试夹具的 session 初始值、Mock 断言及 Windows 证书探测关闭处理已修正。未把测试失败登记成产品通过。
- 已有 UTC/Pydantic 弃用提示仍需另行维护，不是本次 TLS 故障；不因此宣称所有代码已无问题。无前端运行时变更，不用重新设计 UI。

## 5. 已核对的发布证据（2026-10-06）

- 修复源提交：`d3d768d07e4bc94584f03d4256b87e00fef595c1`。
- PR：[#12](https://github.com/kissow/Marzban/pull/12)；PR CI `37486329103` 成功。
- 合入 master / 运行时 OCI revision：`eb43761ebcea3e62d550621982a6442cfbcddf62`。
- 正式构建：[Actions 37486719383](https://github.com/kissow/Marzban/actions/runs/37486719383)，完成时间 `2026-10-06T15:31:59Z`；后端检查、前端检查/构建、Xray pin 和镜像发布全部成功。
- 镜像：`ghcr.io/kissow/marzban:latest`；index `sha256:569aa43f94fdfc7711a05c20c2e498c782ac625cd0e7e38b64503788ab1fbbcb`。
- linux/amd64 manifest：`sha256:ca3dc61809124339f26922908b115c321fdeb5c24ce5e5ddeb35525126e4a58d`；config `sha256:e5664b41bb02646260f7b6c82a41672f51e503f990a80665225fb7721556f15e`。
- linux/arm64 manifest：`sha256:889d8f6acd1b548431fbfd054b541356aaecfc4ef33a5afe4ca6ae7703bbef07`；config `sha256:bf3d72427bfc6eb32af3086c99eb922e8e9bf1e1e3666785f14e293ce5f8171d`。
- 核验时间 `2026-10-06T23:34:29+08:00`：index/manifest/config 原始字节 SHA256 与声明一致，两架构 revision 均匹配合入提交，验证前后 latest 未变化。
- Node/scripts 无本轮运行时/协议/命令变化，无需重复构建或服务器更新；Xray 正式基线仍为 `v26.3.27`。

## 6. SSH 更新与服务器验收（待用户执行）

以下命令在已切换 Fork 的主控服务器执行；保留更新脚本生成的升级前备份，不重装、不删除卷、不覆盖 `.env`。拉取镜像可能耗时数分钟，更新过程中会短暂重启服务。

```sh
marzban update
marzban status
marzban logs --no-follow 2>&1 | tail -n 100
docker ps --filter label=com.docker.compose.service=marzban --format '{{.ID}}' | xargs -r docker inspect --format '{{.Name}} | {{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

期望运行镜像为 `ghcr.io/kissow/marzban:latest`，revision 为 `eb43761ebcea3e62d550621982a6442cfbcddf62`。后续仅文档提交 SHA 不应替代本运行时 revision。

1. 推送、干净 Linux CI 及双架构发布核验已完成；服务器还未由本轮工具远程更新或验收。
2. 确认服务器已切换到本 Fork，再使用 `marzban update`；保留升级前备份。禁止重装、删除数据卷或覆盖 .env。
3. 核对运行镜像的本轮 revision、Xray v26.3.27、两个 Node 的控制/API 端口、证书和用户数据。
4. 在隔离测试节点模拟控制延迟/断连：超时必须显示真实阶段原因；不得因一次健康读取失败触发会话接管或运行核心重启；另一个健康节点继续采集/恢复。
5. 恢复网络后观察 API 迟到恢复；Node 服务重启产生明确 Session mismatch 时，允许重新建会话并同步策略/账号。不要在有用户的正式节点强制断网验证。
6. 控制与 API 稳定观察至少 30 分钟；实际手机/桌面客户端流量、账号和订阅可用；证书/认证错误仍被拒绝。若持续失败，继续检查服务响应、网络路径、防火墙及 API 就绪情况，不能把提高期限当作网络已修好。
7. 只有实际验收证据齐全才标记服务器通过；这份记录表示镜像已发布，不表示服务器已部署或网络已稳定。
