# MR-20261006-NODE-RECOVERY：节点连接恢复检查

维护者：Mr.shaw。2026-10-06（Asia/Hong_Kong）本地完成；尚未提交、推送、运行本轮 Actions、发布镜像或执行服务器验收。下述测试不代表生产网络已恢复，旧发布记录的摘要不能作为本轮镜像证据。

2026-10-06 已获维护者授权同步线上仓库并构建。先通过修复分支/PR 合入 master，再核对 Actions 和实际新镜像；发布证据核对后补充本文件，不提前标记服务器验收通过。

## 证据和修复范围

用户提供的主控日志显示 REST 控制请求超时和 Xray API readiness 超时；Node 日志显示 `/restart` 成功后出现 `/disconnect`、核心停止和失效会话的 `/ping` 403。当时监听检查只有控制端口 62050，没有 API 端口 62051。`Xray is started already` 是原有 start→restart 回退情形，不足以证明核心崩溃；失效控制会话的 403 也不是 HWID 拦截。日志不能唯一确定是谁调用了 disconnect。

代码审查确认了生命周期并发、失败重启无条件 disconnect、健康异常影响后续节点、TLS 握手缺乏期限等风险。本轮修复这些主控路径；生产故障是否完全解决仍须部署后验收，不能把代码风险当成已证明的唯一生产根因。

- 每个 Node 独立的可重入锁：连接、重启、管理修改/删除及健康检查串行；重复重连合并，明确的配置重启等待执行，不同节点可以并行。
- 自动失败恢复等待 30 秒再尝试，保留错误原因；手动重新连接不受该退避限制。健康检查跳过正在操作或退避中的节点。
- 复用会话失效的 transport，而非先 remove/disconnect；启动或重启失败不再无条件停止远程核心。真正修改、禁用、删除和服务退出仍保留其原有断开行为，不承诺更新过程零中断。
- 从数据库检查全部启用的节点，包括 transport 尚未创建成功的节点；隔离各节点异常，主核心恢复失败也不会阻止检查子节点。
- 异常写入既有 `message`，区分配置读取、transport 构造、控制会话/TLS、配置/健康、核心/API readiness、版本读取阶段；最终清理等待状态和锁。
- API 就绪并读取版本后标记 connected；健康恢复可清除旧 error/connecting，不重复重启健康节点，也不每轮重写健康节点状态。无新版本响应时保留已知版本。
- 全用户设备账号的既有 best-effort 协调在节点锁释放后执行，避免大量用户协调拖住节点生命周期；没有修改设备限制策略。
- REST/RPyC 取证书、RPyC TCP/TLS 握手采用 5 秒阶段超时，保留证书校验及 RPyC 双向 TLS；部分连接失败关闭，EOF 最多尝试四次。RPyC 同步请求仍为 10 秒。REST 核心 API 5 秒就绪失败明确实际 API 端口及监听/防火墙提示。

超时是网络阶段期限，不是整个工作流的硬截止：DNS、数据库、配置生成不在全局计时范围。锁适用于原有单进程服务，不是跨 worker/多主控的分布式锁。保留 upstream Marzban、Marzban-Node、Xray 署名及许可证；使用 Python 标准库和 RPyC 公开接口，没有复制外部项目源码。

## 接口与兼容登记

| 既有接口/组件 | 本轮行为与边界 |
| --- | --- |
| `GET /api/nodes`、`GET /api/node/{node_id}` | 权限、字段不变；既有 status/message/xray_version 展示恢复状态与阶段性错误 |
| `POST /api/node/{node_id}/reconnect` | 原 sudo-admin 权限和异步响应 `{"detail":"Reconnection task scheduled"}`；200 表示接受任务，不代表成功连接，重复进行中的任务可以合并 |
| `PUT /api/node/{node_id}`、`DELETE /api/node/{node_id}` | 请求/响应/权限不变；数据库和 transport 改变与恢复任务使用同一生命周期锁 |
| Node REST、RPyC、健康/设备策略通道 | 无线协议、方法、字段或认证变更；原版与配对 Node 兼容测试通过，既有新出口能力要求不变 |
| `kissow/Marzban` | 本地代码已修复，部署本轮修改前需要新的主控镜像；本轮尚未发布 |
| `kissow/Marzban-node` | 无服务端代码或协议变化；已配对 Node 不需本轮构建/服务器更新 |
| `kissow/Marzban-scripts` | 无安装/更新命令或运行时变化；无需本轮构建/更新 |

没有新增端口、UI、数据库迁移、环境设置、证书变更、HWID/订阅/UDP 策略或核心升级。正式基线仍为 Xray `v26.3.27`。保留用户、数据库、配置、证书和数据卷。

## 本地重复验证

- 固定 PowerShell 7 / 项目 Python 3.12.14，所有测试、缓存、构建产物仅在项目 F 盘目录。
- 同一最终运行时代码两轮完整 unittest 均 `95/95` 通过。连接编排文件共 30 项，新恢复文件共 12 项，其余协议、设备/订阅、出口和调度器回归一并运行。
- 覆盖真实 socket/TLS 握手停滞、RPyC 新/旧服务 mTLS、不信任证书拒绝、部分连接清理；REST readiness 端口提示、健康任务隔离、生命周期串行、重复重连合并、自动退避/手动绕过、账号协调释放锁及健康状态恢复。
- TypeScript `tsc --noEmit`、Vite 生产构建、Python compileall、pip check、固定入口 Check 和 `git diff --check` 通过。构建产物位于 `.cache/verification/node-recovery-dashboard`。
- 既有 datetime.utcnow/Pydantic json 弃用和 Vite 大 chunk 提示仍登记保留，不屏蔽；不是本轮连接修复新增的错误。不宣称整个项目绝无 BUG。

## 发布与服务器验收闸门

- [x] 本地修复、重复回归、兼容边界与接口文档登记。
- [ ] 本轮源提交/推送：未执行。
- [ ] 本轮 Actions、双架构镜像摘要和 OCI revision：未执行、无新证据。
- [ ] 服务器更新与真实网络验收：未执行。

获得发布授权后按 RELEASE_CHECKLIST 和 REPOSITORY_UPDATE_FLOW 记录本轮源/Actions/新镜像证据，再提供服务器更新步骤；不能以当前 latest 的历史镜像宣称部署本轮代码。更新前保留数据库、环境、证书、配置、数据卷及实际旧镜像摘要，不 reinstall、不删卷。

部署后用隔离节点验证：正常初连和原版重连；控制端口/TLS 不可达；API 端口不监听；修复后自动恢复；连续重连；多个节点中单个异常；修改/禁用/删除时状态；实际订阅和应用访问。核对 error 的具体 message，不允许长期无原因 connecting。API readiness 成功只是管理连接验收，还需验证用户访问。不要在已有用户的生产节点上制造断网故障。
