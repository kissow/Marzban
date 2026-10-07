> 本功能已包含MR-20261008配对发布；[当前精确镜像/SSH/验收证据](NODE_RELAY_SOURCES_RELEASE.md)。下文未发布/需CI等文字记录原本地阶段，不代表当前latest；服务器与真实UI验收仍待完成。

# MR-20261008-NODE-RELAY-SOURCES

状态：配对代码已合并，干净Linux CI和双架构镜像已发布核对；服务器、真实UI及多引擎数据库验收待完成，不标稳定版。[精确发布和SSH证据](NODE_RELAY_SOURCES_RELEASE.md)。维护者：Mr.shaw。

## 功能和界面

原节点页的“连接方式”改为与住宅出口相同的“管理”入口，使用原 React/Chakra 弹窗、主题、信息图标。说明支持悬停、键盘焦点/Escape 和手机点击；保存独立于原 Node 表单。保留原证书、名称、地址、开关、控制/API 端口、倍率及父窗口宽度。

可选择两种中转来源：

- Marzban 主服务器 → 目标 Node。
- 源 Node → 目标 Node，由 Marzban 通过既有认证通道统一下发。

客户端 → 所选源服务器的业务监听端口 → 目标 Node 的业务入站 → 目标出口。每个目标 Node 一个来源/一个业务入站；同一源可管理多个目标。源 Node 自身的直连订阅和出口不变，源住宅出口不参与此透明转发。目标继续负责 VLESS/REALITY 认证、现有设备凭据及住宅出口；转发不改变既有 HWID 兼容范围，不宣称精确物理设备限制。

首版仍为 VLESS TCP/RAW REALITY、IPv4/DNS-only 入口，透明 TCP 转发，不终止 REALITY。不增加共享账号，不更换证书，不升级 Xray，固定 v26.3.27。并非所有协议均已验收；不新增独立 UDP 监听，目标对隧道内 UDP 的处理仍取决于原协议/出口。REST/RPyC 是控制通讯，不承载用户业务流量。

原 Hosts 精确匹配规则见 [内部订阅合同](NODE_RELAY_SUBSCRIPTION.md)。保留原别名、顺序、条目数量与凭据，不再追加 `(Relay)`；只替换匹配条目的实际地址/端口。失败/未监听时保留原直连输出，不保证直连公网可达。必须刷新客户端订阅；旧客户端残留条目按客户端更新规则清理。

这是单跳选择，不会将多个 Node 中转设置自动串成多跳链。禁止自己到自己、同控制地址的源/目标及配置环路；不通过 DNS 猜测不同域名为同一机器。管理员应避免用不同域名/IP 别称隐藏相同源/目标。

## 管理 API

既有 sudo Bearer 认证、路径不变，非管理员/非 sudo 仍为 401/403：

| 方法/路径 | 用途 | 本轮变化 |
| --- | --- | --- |
| GET `/api/nodes/relay/options` | 来源和可用业务入站 | 增加 `sources=[main,node]`、`source_nodes`（id/name/address/connected）、`required_node_capability` |
| GET `/api/node/{node_id}/relay` | 此目标配置/状态 | 增加 `source=main/node`、`source_node_id` |
| PUT 同路径 | 保存/切换/取消来源 | `source=node` 必须提供正整数 `source_node_id`；main 不得指定 Node ID |
| DELETE 同路径 | 恢复此目标原直连 | 清理旧源监听，只删除此目标 relay 行 |

```json
{
  "mode": "relay",
  "source": "node",
  "source_node_id": 1,
  "entry_address": "relay-node.example.com",
  "allocation": "auto",
  "listen_port": null,
  "inbound_tag": "VLESS TCP REALITY"
}
```

在目标 Node 的弹窗选择来源，入口地址填写所选源服务器的直连 IPv4/DNS-only 域名，不是目标地址、面板网页 URL 或 CDN 地址。自动端口从18443起、尽量复用旧端口；手动1024–65535。检查配置端口、控制/API 端口、其它目标已分配端口和源服务器实际监听占用。当前数据库端口唯一约束保守地跨来源全局去重，同端口不在多个源上复用；每源快照最多512个目标，不是512并发性能承诺。

目标不存在404；字段/未匹配Host/缺失或离线源/旧Node能力/自转发/环路/端口预检422；运行时绑定/源ACK/传输失败409；数据库异常500并尝试恢复旧快照。失败原因保留；回滚失败会明确报告，不广告新端点。`source_nodes.connected` 是当前主控记录，不保证实时能力或网络；保存时再核对能力与核心状态。

`running` 只代表主服务器的监听验证或源 Node 最近一次完整 ACK；不是端到端测速、目标可达或公网客户端验收。周期恢复检测丢失/退出的源进程，故障源不发布新端点，其他来源尽力恢复。源之间控制请求有有限期限，但多个慢来源仍可能增加一次恢复耗时，不宣称大规模公网压测完成。

## Node 线协议与生命周期

源 Node 必须支持 `managed-node-relay-v1`；旧 Node 不需要承担新来源功能，保存为 Node 来源时会拒绝不支持者。REST 仍使用原双向证书 TLS、控制端口与 session_id；RPyC 使用原 SSL 认证连接。

| REST POST | RPyC exposed 方法 | 用途 |
| --- | --- | --- |
| `/relays/status`，`{session_id}` | `fetch_relay_status()` | capability、core_started、running、profiles、error、occupied_ports |
| `/relays`，`{session_id,profiles}` | `set_relays(JSON字符串)` | 替换该源完整目标快照；空列表清理 |

RPyC 请求/响应传 JSON 字符串，REST 传原生 JSON，避免远程嵌套 netref 序列化差异。profile **仅允许** node_id/listen_port/target_address/target_port 四字段；不接收任意核心配置、密钥或用户账号。ACK 必须包含相同能力、精确快照和有效监听状态，才改写订阅。REST 写超时不盲目重放；只读状态有限重试。会话接管、失效断开、显式停止清理旧 relay；重连后主控从数据库重新下发。转发使用镜像已有固定 Xray 的独立进程，新增 psutil 5.9.4 依赖用于监听归属检测，无需额外转发软件/监控端口。

每个来源用一个独立转发进程管理完整快照；改变其中一个目标时可能短暂中断同来源其他中转会话，不重启其业务核心。不宣称零中断更新；不同来源的保存不会探测/重写无关来源，周期恢复仍统一检查并隔离失败。

数据库 additive migration `9012ab34cd56` 接在 `8f9012ab34cd` 后，给 node_relays 增加 source（默认main）和 source_node_id（源删除SET NULL）。原 relay 自动保持主服务器来源；原用户、订阅、证书、端口、环境和数据卷不删除。干净Linux CI已通过；真实PostgreSQL/MySQL迁移验收仍待执行；SQLite 旧行升级/回滚本地覆盖不代表所有数据库已验证。

## 发布、升级和验收门槛

本地最终代码复核：主控完整164/164两轮；Node完整60/60两轮，无跳过，均设置固定Xray实测环境；前端47/47、TypeScript/Vite生产构建、pip check、语法编译和三仓库diff检查通过。包含真实本地RPyC嵌套序列化与REST ASGI请求、认证错误、来源切换/删除/周期恢复/无关故障隔离、旧行迁移与监听占用回滚。共享项目Python测试环境不是干净Linux镜像环境；实际mTLS跨服务器/吞吐与数据库多引擎验收待执行。保留既有utcnow/Pydantic弃用和Vite大chunk警告，不把警告隐藏或当失败。

新增测试初次失败为测试辅助函数重复entry_address参数、原disabled断言插入到deleted-source测试尾部；修正测试边界后42项专项和最终全量复跑通过。单独保存某目标不应探测无关离线来源的问题已修复并加入回归，不只记录“多测一次”。

主面板与源Node配对镜像已发布，scripts仅配对文档、不改安装代码。用户授权后已上传/合并，两边Linux CI、双架构镜像和revision已核对；现在update可取得本功能。实际UI截图受浏览器策略阻断、真实服务器验收待执行，不标稳定版。

发布后已切换 Fork 的安装：备份，在承担来源的服务器运行 `marzban-node update`，检查连接/能力/固定核心，再在主控运行 `marzban update`。仅作目标、不作来源的已配对 Node 不因本功能强制更新；若也作为来源就需更新。无需重复 adopt/install，不换证书或原控制/API端口。新服务器沿用仓库一键install流程，镜像发布后才包含新能力。仅放行所选源的业务入口 TCP端口；既有认证端口安全范围保持。

服务器验收：原客户端条目数/别名不变；目标经主控及源Node两种来源均可访问且公网出口仍为目标；源原直连出口/计费不变；切换来源/直连清理旧监听；目标停止、源重连/进程退出/失败恢复原因真实；至少两个目标、桌面/手机、订阅与持续30分钟网络/速率测试。100/200个配置测试是配置范围检查，不是公网并发压测。真实吞吐受客户到源、源到目标及目标出口最慢一段限制。

回滚前先将 Node 来源恢复直连并核对源空快照；保留备份，使用配对旧镜像和经验证的数据恢复方案。禁止删除用户/卷或重装；不要在仍有 source=node 行时直接退回只认识 main 的旧主控。迁移降级会删除新增来源字段，必须先导出配置并评估再执行，不作为常规更新步骤。

感谢 Gozargah/Marzban、Marzban-Node 与 XTLS/Xray-core 原作者及贡献者，保留上游许可。Node 的纯转发模块复用本 Fork 已开发的 Mr.shaw 主控模块，不是复制3X-UI源码；没有新增外部源码借用。
