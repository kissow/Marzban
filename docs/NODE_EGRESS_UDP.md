# 每个 Node 的住宅出口 UDP 策略

初连执行顺序修复（2026-10-03）：非 legacy 出口的健康/能力检查前必须先建立
现有认证会话，然后启动 Node。UDP 模式/能力标识和线协议不变，已配对 Node 本轮不需更新。
修复与依赖维护的发布状态见 [NODE_CONNECTION_RELEASE.md](NODE_CONNECTION_RELEASE.md)。

变更编号：`MR-20261003-EGRESS-UDP`。日期：2026-10-03。状态：代码和配对镜像已发布，实际服务器/手机/供应商/UI 截图验收待完成，未标记稳定版。作者：Mr.shaw。源 SHA、Actions 与 GHCR/OCI 证据见 [发布记录](EGRESS_UDP_RELEASE.md)。

## 为什么按 Node 设置

客户端支持 UDP 不代表每个请求都使用 UDP。不同客户端的 DNS、分流和应用回退方式可能不同；不能只凭一个客户端可用就认定供应商支持 UDP。此次问题日志显示 UDP DNS 请求经住宅 SOCKS5 代理被拒绝，但共享 Node 日志不能把所有失败归因于同一客户端。此次修改不改变 HWID/设备登记策略，也不假定手机或 TUN 不兼容。

沿用原 Chakra 的住宅出口表单，仅增加“UDP 处理”：桌面为“协议/UDP 处理、服务器/端口、用户名/密码”三排；手机单列。保留证书、节点端口、启用开关、其他原控件及原弹窗宽度。使用真实组件预览，不另做设计稿。

## 模式合同

| `udp_mode` | 行为 | 适用范围 |
| --- | --- | --- |
| `legacy` | 默认保持此前行为：SOCKS 默认 TCP/UDP 走住宅代理，HTTP 默认只接管 TCP | 老数据/老 Node；线协议省略该字段 |
| `proxy` | SOCKS 默认 TCP/UDP 走住宅代理，不重写 DNS | 供应商确实支持 UDP ASSOCIATE；HTTP 不接受此模式 |
| `tcp_only` | 默认 UDP53 DNS 交给 DNS 出站，DNS 上游经住宅代理走 TCP；其他默认 UDP 阻断，默认 TCP 走住宅代理 | 不支持 UDP 的供应商；不是任意 UDP 转 TCP |

“默认”指未被原有显式 API、安全、域名、IP、入站等规则提前匹配的流量。新规则放在原有通用兜底之前，保留显式路由优先级；**已有显式直连规则依然可以直连**，不能把本功能称为全流量防泄漏保证。本修改不额外添加直连降级。

`tcp_only` 在该 Node 配置副本中把 `dns.servers` 替换为 `tcp://1.1.1.1`、`tcp://8.8.8.8`，保留 hosts/queryStrategy 等其他 DNS 字段，并使用内部专用 DNS tag。A/AAAA 使用该内置解析器；其他 DNS 查询通过 DNS 出站 TCP 隧道处理。供应商必须允许相应 TCP53 连接；自定义域名 DNS 分流会被替换，需管理员确认。语音、游戏、QUIC 等其他 UDP 不会因此获得支持；应用是否回退到 TCP 由应用决定。

内部保留 tag：`managed-residential-dns`、`managed-residential-dns-query`、`managed-residential-udp-block`。配置存在同名 tag 时拒绝，不覆盖原配置。Node 在副本中完整验证，失败不写入半套配置；最终配置仍由固定 Xray 预检。

## API、认证与下发

- 路径不变：`GET/PUT/DELETE /api/node/{node_id}/egress`，仍需要 sudo 管理员认证。
- PUT 新增 `udp_mode`，省略为 `legacy`；GET 配置存在时返回保存的模式。协议/服务器/端口/用户名及原密码留空保留规则不变；API 不返回密码。
- 能力：`legacy` 需要 `managed-outbounds-v1`；非 legacy 还需要 `managed-outbounds-udp-v1`。旧/离线/能力不足的 Node 在保存前返回 409；非法模式或 HTTP+proxy 返回 422；认证失败仍 401/403，未知 Node 404。
- 成功保存只表示数据库写入并排队异步重启，不代表供应商连通性验收成功。重连/重启时再次检查非 legacy 能力，防止降级 Node 静默忽略策略。
- 原有认证 REST/RPyC Xray 控制通道传输 `marzban_node_extensions.outbounds[0].udp_mode`，不增加接口、证书或公网端口。只改对应 Node 的配置副本，不改主核心出口。

## 数据、升级和回退

主面板新增 Alembic `7e8f9012ab34`，父版本 `6d7e8f9012ab`，只给 `node_egress` 添加非空 `udp_mode` 字段，旧记录默认 `legacy`。不删除用户、节点、代理凭据、证书、环境文件或数据卷。固定核心仍为 `v26.3.27`，scripts 无变化。

**此功能已发布配对 latest，镜像源 SHA 和摘要已核对；服务器仍待验收。** 先更新配对 Node、验证主面板连接，再更新主面板并为测试 Node 选择模式。已切 Fork 的原部署只 update，不重复 adopt、不重装、不删除卷。升级前备份数据库和部署配置。

回退：先恢复目标 Node 为 legacy 并确认生效，再回退配对镜像。旧主面板不能理解新增字段；数据库降级仅移除新字段，需停服务并先备份，不能删除整个表或替换用户库。若 Node 降级但仍保存非 legacy 模式，主面板会报能力不兼容而不是静默放行。

## 本地验证与待验收

- 主面板完整 unittest 54 项、Node 完整 unittest 48 项通过；核心测试设置 `XRAY_TEST_BINARY`，无跳过。
- 真实固定 Xray：HTTP/SOCKS × legacy/tcp_only × 有/无认证，8 组配置解析；4 个 A/TXT DNS 运行测试使用本地 TCP-only 模拟供应商，验证收到 DNS 回复且发送 CONNECT/TCP53，不使用 UDP ASSOCIATE。
- 迁移升级/回退、单 Node 隔离、密码加密/保留、模式校验、标签碰撞、原子失败、显式路由优先级均有测试。其他 UDP 的阻断目前是路由单元测试，不等于所有实际应用验收。
- TypeScript、生产 Vite 和原组件预览构建通过。浏览器本地安全策略校验失败，未完成真实桌面/手机截图，不宣称 UI 已验收。
- 待完成：原组件桌面/手机 UI 审核、隔离 Linux 主面板/Node 联调、实际供应商 TCP53、v2rayNG/Clash Meta 同账号同节点对照、应用 TCP/UDP/出口 IP、切回 legacy 和另一支持 UDP 的供应商回归。
- 有真实用户连接的节点不得为了排查全量关闭住宅出口或改设备策略；先用测试用户/隔离 Node，日志隐藏凭据。

## 上游和参考

保留 Gozargah/Marzban、Marzban-Node 和 XTLS/Xray-core 原作者与许可证。本次实现为 Mr.shaw 扩展；参考下列上游行为，未复制供应商或其他面板源码：

- Xray DNS 出站：[dns.go（固定 v26.3.27）](https://github.com/XTLS/Xray-core/blob/v26.3.27/proxy/dns/dns.go)、[dns_proxy.go](https://github.com/XTLS/Xray-core/blob/v26.3.27/infra/conf/dns_proxy.go)。
- 客户端 DNS 对照：[Mihomo DNS 配置](https://wiki.metacubex.one/config/dns/)。它用于解释不同解析传输，不是实际手机配置的证据。
