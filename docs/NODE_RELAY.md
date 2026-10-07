> 本功能已包含MR-20261008配对发布；[当前精确镜像/SSH/验收证据](NODE_RELAY_SOURCES_RELEASE.md)。下文未发布/需CI等文字记录原本地阶段，不代表当前latest；服务器与真实UI验收仍待完成。

> 后续本地修复 **MR-20261007-RELAY-INTERNAL-SUBSCRIPTION**：改为保留原条目和别名、内部替换端点，不再额外输出 `(Relay)`；[新合同与状态](NODE_RELAY_SUBSCRIPTION.md)。尚未发布，以下 d2350203 发布记录及额外条目行为仅描述旧镜像，不能当作本轮实现。用户报告旧中转条目已可用，持续公网/多客户端验收仍未完成。

# MR-20261007-NODE-RELAY：Marzban 主服务器中转到 Node 节点

状态：2026-10-07 代码已合并、新镜像已发布并核对双架构摘要/revision。Linux CI（含真实固定Xray进程）通过；用户授权先发布，实际界面截图因浏览器策略blocked，公网REALITY/手机/实际提速验收仍待执行，未远程更新服务器。本轮不冒称稳定发布。

## 1. 使用范围

在原节点设置中，每个已保存的 Node 有一个可折叠“连接方式”区域，可选择直连或通过主服务器中转。首次只接入现有 **VLESS TCP/RAW REALITY** 入站，主服务器为唯一中转来源；不改变其它协议，也不宣称已支持任意 TCP/UDP 协议。

- Marzban 主服务器直连的原主机条目不改，仍使用主服务器原出口；主服务器可部署在任意地区。
- 选择新增的 `Node 名称 (Relay)`：客户端连接 Marzban 主服务器中转入口，再转到该 Node 的原业务入站，出口为目标 Node 或其已配置的住宅出口。
- 每个 Node 一个中转配置、一个独立业务入口端口；不同目标互不混用。原直连主机条目保留作为回退，不覆盖 `/api/hosts` 数据。
- 新建 Node 须先保存，再展开该 Node 的连接方式。首版目标为 Node 原控制地址对应服务器的所选业务入站端口；不支持另填与控制服务器不同的目标业务服务器。

路径：`客户端 → 主服务器:中转入口端口 → Node 地址:业务入站端口 → Node 出口`。

## 2. 控制和数据分离

REST/HTTPS 或原 RPyC 是面板配置、认证、健康统计通道，不承载本功能的用户数据。中转使用现有固定 Xray **v26.3.27** 二进制，启动一个独立受管理进程，`dokodemo-door` 固定目标 TCP 转发、`freedom` 出站，不安装额外软件，不增加控制/API/监控端口。

不终止/重新签发 REALITY，不生成共享中转账号、不改变 UUID/设备独立凭据、SNI、公钥、私钥、short ID 或原认证通道。目标 Node 继续按原账号执行认证和用量统计，主服务器的普通 Xray 用户流量不因本转发进程再计一次账号流量；机器级网卡流量则会包含中转数据。此行为不是物理设备限制增强。

Node 在网络层看到的来源是中转服务器 IP；本轮没有添加 PROXY protocol 或声称保留真实客户端 IP。认证凭据保持原值。住宅代理本身的 TCP/UDP 能力仍决定最终业务能力。

## 3. TCP 和 UDP 边界

固定 TCP 转发可以承载基于 TCP 的其他应用协议，但**首版产品选择器与订阅生成仅接入 VLESS TCP/RAW REALITY**。理论上可转发不等于本产品已实现/验收对应协议。

若应用 UDP 被客户端和目标代理协议封装在 TCP 连接中，该连接仍可穿过中转；这不等于任意 UDP 自动转换为 TCP。Hysteria2、TUIC、WireGuard 等原生 UDP 传输需要独立 UDP 转发、映射/超时及防火墙验证，当前未实现；不删除已有其它协议和供应商能力。Xray 文档现版将 dokodemo-door 命名为 Tunnel，字段名称可能不同，不能直接替换本项目固定版本的已验证配置。

参考 [Xray Tunnel 官方说明](https://xtls.github.io/en/config/inbounds/tunnel.html)。本功能为 Mr.shaw 在原 Marzban 结构中的扩展，感谢 Marzban 与 Xray 原作者/贡献者；未复制 3X-UI 源码，保留原许可证和上游致谢。

## 4. 部署前提与端口

- 沿用原官方主控 `network_mode: host`、单面板 worker；自定义 bridge 容器须额外映射业务端口，首版没有自动修改 compose/firewall。
- 中转入口填写**主服务器公网 IPv4 或仅 DNS 解析到该 IPv4 的域名**，不是带 CDN/HTTP 代理的面板域名，不含 `https://`、端口、路径或凭据。首版监听 `0.0.0.0`，不是 IPv6 入口。目标 Node 可使用 IPv4/IPv6 或域名。
- 默认从 `18443` 起自动分配，重复保存尽量保持原端口。手动端口为 `1024..65535`；避开主核心业务端口、面板端口、所有节点控制/API端口、其它中转端口和当前 TCP 监听端口。
- 自动分配不会自动放行云安全组/主机防火墙。管理员仅放行选中的业务 TCP 端口；目标 Node 原业务端口须可从主服务器连接。
- 中转进程仅转到预先配置的目标，不接受客户端指定任意地址；目标业务协议仍需用户认证。仍须限制入口滥用、评估流量费用/攻击风险。

## 5. 管理 API

认证统一沿用 `Authorization: Bearer <token>` 与 `Admin.check_sudo_admin`：无效身份 `401`，非 sudo 管理员 `403`，不存在的 Node `404`。不新增独立 Token。

| 方法与完整路径 | 用途 | 请求与副作用 |
| --- | --- | --- |
| `GET /api/nodes/relay/options` | 读取允许的来源、候选业务入站、默认入口地址和自动端口起点 | 只读，不启动/保存中转 |
| `GET /api/node/{node_id}/relay` | 读取该 Node 中转配置及本地运行状态 | 只读，不发起 Node 重连 |
| `PUT /api/node/{node_id}/relay` | 设置或切回直连 | 校验、应用独立转发进程后提交专用数据库记录；不修改原 Node/Hosts/证书/核心配置 |
| `DELETE /api/node/{node_id}/relay` | 取消该 Node 中转 | 与 `{ "mode": "direct" }` 相同，仅删除专用记录并撤去虚拟订阅条目 |

示例请求（示例域名不可作为真实部署值）：

```json
{
  "mode": "relay",
  "source": "main",
  "entry_address": "main.example.com",
  "allocation": "auto",
  "listen_port": null,
  "inbound_tag": "VLESS TCP REALITY"
}
```

`mode`: `direct|relay`；`source`: 仅 `main`；`allocation`: `auto|manual`；手动须传整数 `listen_port`；中转须传入口地址和兼容入站标签；未知字段拒绝。Node 禁用或选中入站缺失/不兼容为 `422`。地址、端口或请求校验失败为 `422`；端口唯一冲突、Xray 配置或启动失败为 `409`，保留原因；数据库不可用可为 `500`，先恢复旧中转配置，不能当作保存成功。

GET/PUT/DELETE 响应包含 `configured`、`mode`、`source`、`entry_address`、`allocation`、`listen_port`、`inbound_tag`、`target_address`、`target_port`、`status`、`error`。直连时可空字段为 null，`configured=false/status=inactive`。

`status`：`inactive`（未配置或禁用）、`pending`（未就绪）、`running`（本地 Xray 进程及该监听配置已就绪）、`error`（本地配置/进程失败）。**running/PUT 200 不是主服务器到 Node 的公网连通证明，也不是客户端 REALITY 握手成功证明。** 状态端口不另开。无 API 弃用/删除。

## 6. 保存、恢复和订阅

先执行固定版本 Xray `-test`，通过后才停止旧中转进程；启动后核对进程实际拥有目标监听端口，未就绪不发布新虚拟入口。启动失败尝试恢复上一份配置；数据库提交失败回滚记录并恢复旧转发配置，恢复本身失败须记录原因。

主服务器统一管理一个中转进程，修改任一监听配置会短暂中断**所有该进程中的中转连接**，不是只影响一个 Node；不重启 Marzban 主服务器直连核心或 Node 核心。名称/入口展示地址等不影响实际监听的元数据变化不重启进程。

启动和每 15 秒加载专用表恢复进程；禁用/删除 Node 或入站不再兼容时移除对应虚拟入口，原直连主机不改。Node 的普通修改沿用原生命周期操作并安排中转刷新。多 worker/多实例并行操作同一表不在首版支持范围。

新增虚拟条目走原订阅生成函数，同一入站的参数/同一用户凭据不变，只替换连接地址、端口、名称。用户须更新订阅并选择带 `(Relay)` 的条目；先前导入的 Node 直连条目不会自动经过 Marzban 主服务器。支持该 REALITY 协议的 v2ray、v2ray-json、Clash Meta、sing-box 格式已回归；经典 Clash/Outline 沿用不支持 REALITY 的原行为，不宣称增加协议支持。

## 7. 数据迁移与回滚

新增 Alembic `8f9012ab34cd`，父版本 `7e8f9012ab34`，只新增 `node_relays`：一 Node 一行（FK/cascade），监听端口唯一。原 users/nodes/hosts/tls、`.env`、证书、数据卷不覆盖、不清空。无新环境参数、安装命令或 Xray 升级。

发布/升级前须备份数据库、配置和证书；回滚前先切所有中转为直连、恢复原订阅，再回退镜像。该迁移 downgrade 只删除新增表，不修改旧用户/节点/证书；操作前仍须备份，禁止 `down -v`、重装或删数据目录。SQLite 小型升级/回滚测试通过，PostgreSQL 真机与完整旧安装升级仍待验收。

## 8. 本地证据和防复发

- 最终相同代码全量后端连续三轮 **142/142**（4.930s / 5.189s / 4.733s）；新中转 26 项（含两项真实进程），旧功能 116 项。此前 140/140 与补充 IPv6 入口校验后的 141/141 各连续三轮通过。增加迁移链单 head 回归，手动保存/切回直连循环 10 次无重复条目。
- 真实固定 Xray v26.3.27 仅在本地 loopback 上验证两个目标的 TCP/TLS 传输、端到端证书未替换、崩溃后恢复、元数据不重启、占用端口失败恢复；不是生产 REALITY/手机联调。
- API sudo 权限、404/422/409、数据提交故障回滚；100 个固定转发配置、保留用户/证书、迁移升级/回滚、HWID 私有 UUID/vision 流和主直连订阅保持原值已回归。100 配置测试不是 100 个公网并发连接压测。
- 前端 **44/44**（原 40 + 新 4）连续三轮，生产/原组件预览 TypeScript、生产 Vite 构建、compileall、pip check 与固定入口 Check/diff 检查通过，保留既有 chunk-size/CRLF 提示。datetime/Pydantic 既有弃用提示没有冒充新功能失败，也未顺带重构。
- 本地预览为原生产组件，接口数据为演示、保存仅写内存；不能当作生产后端联调。浏览器 admin-enforced policy 无法核验，截图与界面交互验收为 **blocked**，不绕过策略。
- 实现期间发现并修复 subscription→service→DB 的循环导入（改为延迟导入）、原 AST 路由测试 namespace 未适配、React Query onError 返回值类型错误、自动端口预览显示未保存手动端口；重跑后才登记通过。订阅测试夹具须显式传 DB 风格的 flow 字符串，不使用未验证的 enum 默认值来替代实际返回值。
- 本地测试入口保持 PowerShell 7/UTF-8、项目内 Python/缓存。普通 CI 后端142项中两项显式进程测试先skip；本次两条工作流随后单独准备Xray v26.3.27，并显式设置 MR_SHAW_RELAY_TEST_XRAY 运行两项真实Linux TCP/TLS/恢复测试，已通过。因此140项普通回归加2项真实进程均实际执行，但不是生产REALITY/公网手机客户端验收。
- 追加检查中，单独读取 Alembic head 会经旧 TLS 迁移导入 app、隐式要求生产 Xray，导致本地命令失败。未修改旧迁移或更换环境；改为已有隔离版本启动夹具中读取 head 并补测试，验证唯一新 head/父版本。此环境入口失败不冒充生产迁移失败或通过。

## 9. 上线验收清单（待执行）

1. 原组件桌面/320–390px 手机、深浅主题，展开/折叠、自动/手动端口、提示/错误/重复保存；证书、倍率和原字段仍在。用户已授权先发布，实际截图审核仍待完成，不登记为通过。
2. 干净 Linux CI、迁移、镜像双架构/OCI revision；不能复用旧 latest 发布摘要。
3. 备份后以 fork update 升级主控；本轮 Node/scripts 无运行时或认证协议变化，无需本轮配对更新。
4. 放行一个测试业务入口；验证主服务器原直连出口不变、目标 Node Relay 入口为 Marzban 主服务器而出口为目标 Node/其住宅代理、第二个 Node Relay 使用各自出口。原 Node 直连作为回退。
5. v2rayN/v2rayNG/Clash Meta 更新订阅并选正确条目，测 HTTPS、DNS、封装 UDP 和住宅出口供应商边界；验证共享兼容及 HWID 私有账号均无回归。
6. Node 失联、端口冲突、主控重启、保存失败/取消/禁用/删除；核对原因、恢复和旧数据。公网丢包/容量问题不是代码可保证消除的。
7. 三段链路分段测速、CPU/内存、TCP 重传及至少 30 分钟运行观察；Marzban 主服务器总带宽/目标 Node 出口/住宅供应商任一均可成为瓶颈，两台服务器可能均计费。不承诺中转必然提速。

本轮发布授权、源/合并提交、Actions及镜像均已核对，详见第11节；界面和服务器验收仍待执行，不用历史发布替代本轮证据。

## 10. 对照测速（更新后执行）

先更新客户端订阅，确认新增 `(Relay)` 条目；入口是 Marzban 主服务器、出口应为目标 Node/其住宅代理。保持同一电脑/手机、客户端、路由/TUN 设置和测速站点；尽量同一测速服务器，低峰无其它下载。依次测 Marzban 主服务器直连、目标 Node 直连、同一目标 Node Relay，每种三轮，记录下载/上传 Mbps 和空闲/负载延迟，比较中位数。fast.com 测量到 Netflix 的链路，不能代表所有线路；YABS 的服务器到其它测速机结果不是客户端这条链路。[FAST 官方说明](https://fast.com/)。

主服务器直连须保持其原出口；目标 Node Relay 须使用对应 Node 或其原住宅代理出口。必须验证 v2rayN/v2rayNG/Clash Meta 实际联网与至少30分钟观察；面板 running 只证明监听就绪，不证明提速。160 Kbps=0.16 Mbps，不能与服务器 Mbits/sec 忽略单位直接比较。

若 Relay 仍慢，可选临时 iperf3 测 Marzban 主服务器→目标 Node 段，不修改 Node 控制/API端口。两台先运行 `iperf3 --version`；没有安装时可由管理员在 Ubuntu 上安装 `apt-get update && apt-get install -y iperf3`，不是本功能必须依赖。仅在目标 Node 云安全组/防火墙临时允许 **来自 Marzban 主服务器公网IP** 的 TCP 5201，不对全网开放；低峰运行，注意流量和在线用户。

目标 Node 服务器 SSH（前台，不作为长期服务）：

```sh
iperf3 -s -p 5201
```

Marzban 主服务器另一个 SSH，输入实际目标 Node IP，不是主服务器中转地址：

```sh
read -r -p '目标Node公网IP: ' TEST_NODE_IP
iperf3 -c "$TEST_NODE_IP" -p 5201 -t 15 -P 1
iperf3 -c "$TEST_NODE_IP" -p 5201 -t 15 -P 1 -R
```

第一条数据主服务器→目标 Node，`-R` 数据目标 Node→主服务器；可重复三轮，必要时对照 `-P 4` 总吞吐，不把多流成绩当单连接速度。结束在目标 Node 服务器 Ctrl+C，删除临时5201规则。[iperf3 官方参数](https://software.es.net/iperf/invoking.html)。

这个测试只测 Marzban 主服务器与目标 Node 之间，不经过真实 REALITY 用户连接，也不测客户端→主服务器或目标 Node→网站/住宅代理。结合浏览器三条目对照、两台 `docker stats --no-stream`、实际流量/重传才能定位瓶颈。不保证中转必然更快，任何一段线路/带宽/住宅代理都可能限制最终速度。

## 11. 本轮发布证据与服务器更新

- 源提交：134f12faf5e29e53986ff271a8c8f57b8a38db38；[PR #16](https://github.com/kissow/Marzban/pull/16)，合并运行时 d23502030358930592016f9ff2f7d3f42acad4e7。
- [PR Linux CI 37637526876](https://github.com/kissow/Marzban/actions/runs/37637526876) 与 [正式构建 37637973415](https://github.com/kissow/Marzban/actions/runs/37637973415) 首次成功；140普通后端 + 2真实Xray进程、44前端、类型/生产构建和核心版本闸门通过。
- 镜像 ghcr.io/kissow/marzban:latest；index sha256:252adac60cdcbcc83a7ef13a080d52876876017a65220c58fcf76539db9ccd03。
- linux/amd64 manifest sha256:1766ed650d74242fb5119244ba2a0cae67e5d9037415f3abd62819ca15e7c82c；config sha256:fcd8ee6c295ef7c8bbeed67ae7279ade1c0603d98df2b7ada327c49c926fb1aa。
- linux/arm64 manifest sha256:4abdbdcc4cc31b8ed225c3d4a9e52b5c1269615008d991ae32f98150c0affba3；config sha256:87e06e24d634796ac9d994c87686297870c6bae2179981fc7cc521fa94bb1c54。
- 两架构 OCI revision 均为 d23502030358930592016f9ff2f7d3f42acad4e7；2026-10-07T22:43:55+08:00核对原始字节哈希、registry digest、前后latest未变化。
- 保留既有Vite chunk-size提示、datetime/Pydantic弃用提示；Actions提示Node20 action运行时弃用/自动迁移24及ubuntu-latest后续迁移，当前构建成功，不在本轮顺带升级工作流依赖。Git文档回写fetch两次连接reset是本地网络失败，不是Actions失败；文档经认证GitHub API回写时单独登记，不冒称Git fetch成功。

已切换本Fork的主控服务器，root SSH执行（非root用sudo）；现有脚本先备份并保留.env/数据，更新短暂重启，外部数据库须另行备份。保留 Pre-update backup 路径，不重装/删卷：

```sh
marzban update
marzban status
marzban logs --no-follow 2>&1 | tail -n 100
docker ps --filter label=com.docker.compose.service=marzban --format '{{.ID}}' | xargs -r docker inspect --format '{{.Name}} | {{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

运行镜像须为 ghcr.io/kissow/marzban:latest，revision须为上面的d23502030358930592016f9ff2f7d3f42acad4e7，核心26.3.27。本轮Node/scripts无需更新。只写文档的[skip ci]提交不改变镜像revision。

刷新页面后，在目标 Node 的“连接方式”选择经主服务器中转，填写 Marzban 主服务器公网IPv4或DNS-only入口，选自动/手动业务端口及该Node原VLESS TCP/RAW REALITY入站并保存。仅放行 Marzban 主服务器分配的业务TCP端口，目标 Node 原入站允许主服务器访问；控制/API端口不改。更新客户端订阅、选对应 Node (Relay)，按第9/10节核对出口/客户端/测速；原主服务器/Node 直连仍在。保存运行中不等于这些验收已完成。
