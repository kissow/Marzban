# Node 活动统计与设备策略合同

状态：2026-10-02，镜像已发布，服务器验收待完成；维护者：Mr.shaw。主面板 Actions `36975384550`、Node Actions `36975383911` 均成功，配对 commit 和 GHCR digest 已登记；服务器尚未部署。

## 数据流与认证

Marzban 通过原有 TLS REST/RPyC 控制通道读取对应 Node 的指标和同步策略；外部调用者使用 Marzban 的 `GET /api/node/{node_id}/health` 和超级管理员 Bearer Token。继续使用现有服务端口及 Xray API 端口，证书、数据目录、数据库和部署命令保持原样。

| 通道 | 请求 | 响应与用途 |
| --- | --- | --- |
| REST `POST /health` | 原有 `session_id` | 资源指标、活动采样及策略元数据 |
| REST `POST /device-activity` | 原有 `session_id` | 仅活动采样，读取不重置计费流量 |
| REST `POST /device-policies` | `session_id`、`policies` 数组 | 完整替换策略快照，返回接收确认 |
| RPyC `fetch_health()` | 原有 TLS 连接 | 与 REST 健康快照一致 |
| RPyC `fetch_device_activity()` | 原有 TLS 连接 | 与 REST 活动采样一致 |
| RPyC `set_device_policies(json_string)` | 原有 TLS 连接、JSON 字符串 | 避免 RPyC 容器 netref 的类型误判；与 REST 同一校验器 |

REST 会话缺失、失效或不匹配返回 403；无效策略返回 422。每批最多 10000 条，`device_limit` 为 0–100000 的整数，0 表示不限；用户标识唯一、长 1–128；模式只允许 `hwid`，动作只允许 `log_only` 或 `reject_new`。整批校验成功才原子替换；空数组清除旧快照。RPyC 接收端也接受本地 Python 数组，但主面板统一发送 JSON 字符串。

## 活动字段及口径

`active_users` 为非负整数或 null，绝不从主机 socket 数量推导。优先使用固定核心 `v26.3.27` 的 `GetAllOnlineUsers`。Node 在既有 Xray 配置的 policy levels 中启用 `statsUserOnline`，保留其他字段。

| 来源 | scope | 口径 |
| --- | --- | --- |
| `xray-online-users` | `online_users` | Xray 在线 IP 表中存在活动条目的用户；同一用户只计一次 |
| `xray-user-stats-delta` | `recent_traffic` | 旧核心未实现该 RPC 时，Node 在默认 120 秒滚动窗口内观察到流量变化的用户，尽力统计 |
| `panel-node-usage` | `recent_traffic` | 旧 Node 没有活动合同，主面板兼容使用最近 2 小时已有节点用量记录 |

响应包含 `active_users_sampled_at`、`activity_source`、`activity_scope`、`activity_reason`。流量回退附带 `active_users_window_seconds`；原生在线查询该字段为 null。面板用量回退附带 `active_users_window_hours`。Node 采样缓存 5 秒；主面板验证采样时间在 15 秒内且最多容许 5 秒时钟超前。

采样首次建立基线或长时间无采样后返回 null/`sampling_baseline`；Stats 失败返回 null/`stats_unavailable`。主面板不会用兼容回退掩盖新 Node 的查询失败。RPC 只有 UNIMPLEMENTED 会触发旧核心回退；网络错误不会伪装成零用户。Node 查询计数器始终使用 reset=false；原有主面板计费 reset=true 继续工作，Node 不抢占计费数据。旧核心回退可能漏掉两次采样间发生且被主面板清零的短流量，不能作为精确在线或结算统计。

## 策略接收与执行范围

示例请求仅包含策略字段：

```json
{
  "policies": [{
    "user": "1.example",
    "device_limit": 3,
    "device_limit_mode": "hwid",
    "device_limit_action": "reject_new"
  }]
}
```

完整快照包含 active、on_hold、limited 用户，排除 disabled、expired 和已删除用户。不会传递密码、订阅 Token、原始 HWID、设备记录或 IP 地址。策略快照本身只含元数据；设备专属代理凭据通过主面板现有的 Xray 控制通道单独下发到主核心和已连接 Node，不放进策略 JSON。

成功响应为 `accepted=true`、`policy_count`、`policy_revision`（规范化快照 SHA-256）、`policy_synced_at`（UTC）、`policy_enforcement=subscription_request_and_node_credentials`、`direct_connection_enforced=true`。健康接口保留以上元数据，主面板还显示 `policy_sync_status`：synced/pending/failed/unsupported。同步成功要求确认数量和执行范围匹配；错误确认标为失败。

Node 启动、重启及重新连接后同步；管理员创建、修改、删除用户后同步；60 秒任务补齐计划任务修改及失败重试。批次按顺序执行，一个批次只读一次数据库、最多并行推送 10 个 Node；单节点失败不阻断其他节点或回滚已保存用户。旧 REST 返回 404/405/501、旧 RPyC 无方法时标为 unsupported，继续原连接功能。

`reject_new` 的执行链如下：订阅请求必须携带 `X-HWID`；主面板只保存 HWID 的 SHA-256，并在登记成功时为该设备按协议生成独立凭据。订阅响应替换为该设备自己的 UUID/密码；主面板随后把相同的设备账号同步到每个已连接 Node。未登记、超额或没有有效设备凭据的请求不会生成订阅。Node 重启时从主面板生成的配置加载这些设备账号，因此直接使用旧共享 UUID/密码的配置在同步完成后不再匹配。

这是真正的“新连接凭据拒绝”而不是实时在线设备数统计：同一公网 IP 下的多台设备仍按不同 HWID 计数；没有发送 `X-HWID` 的旧客户端在 `reject_new` 用户上会收到 `428`，已有旧配置不会被订阅检查主动踢下线。将用户切回 `log_only` 会清理设备账号并恢复共享账号。设备登记表由 `4a9d2e8b7c61_add_user_device_limit.py` 创建，设备凭据字段由最新迁移 `6d7e8f9012ab_add_device_credentials.py` 加入；当前设备限制迁移链的最新 revision 是 `6d7e8f9012ab`，升级不删除原有用户、证书、端口或数据卷。

`policy_enforcement` 的 ACK 只证明 Node 已接收并校验策略快照；直接连接的实际拒绝证据是主面板生成的 Xray 配置只包含已登记设备账号，并且该配置已由 Node 成功加载。`subscription_request_only` 是旧 Node/旧策略元数据的兼容值，主面板仍可读取它以便展示旧节点能力，但当前配对实现应返回 `subscription_request_and_node_credentials`。

## 来源与致谢

本 Fork 保留 Marzban / Marzban-Node 上游历史、许可证和作者署名。Xray 协议依据官方 [StatsService protobuf](https://github.com/XTLS/Xray-core/blob/v26.3.27/app/stats/command/command.proto)、[实现](https://github.com/XTLS/Xray-core/blob/v26.3.27/app/stats/command/command.go) 和 [OnlineMap](https://github.com/XTLS/Xray-core/blob/v26.3.27/app/stats/online_map.go)。本次 wire 编解码及策略验证为本 Fork 自行实现，没有复制其他面板的设备限制源文件。

## 验证、升级与回退

两仓库运行 `python -B -m unittest discover -s tests -v`；主面板运行 `npm exec tsc -- --noEmit` 和 `npm exec vite -- build --outDir build-ci`。Node 设置 `XRAY_TEST_BINARY` 可运行固定核心真实配置预检及 TLS Stats RPC。UI 必须以原 Chakra 组件在桌面/手机渲染后审阅，再推送。

发布记录已补录两仓库 commit、Actions run、镜像 tag/index/架构 digest 和 OCI revision；服务器验收仍待完成，当前不能写成稳定发布。脚本无运行时变更，核心继续固定 `v26.3.27`。已有 Fork 部署发布后使用 `marzban update` / `marzban-node update`，官方旧安装首次切换使用 adopt，新机才使用 install。保留数据库、环境文件、证书、现有端口、配置及数据卷；本轮包含设备凭据数据库迁移，必须先备份后升级。回退到先前配对镜像与保存的配置；旧面板忽略新增指标字段，旧 Node 被识别为不支持新增方法。
