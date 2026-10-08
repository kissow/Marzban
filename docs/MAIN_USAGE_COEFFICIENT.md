# 主面板本机使用系数

变更编号：`MR-20261008-MAIN-USAGE-COEFFICIENT`。维护者：Mr.shaw。
状态：本轮镜像已发布并核对双架构；服务器验收未执行。仅文档回写不重建运行时镜像。

## 设置入口与范围

在原版「节点设置」顶部新增「主面板（本机）」卡片，单独保存，不修改远程 Node 表单。原 Chakra 主题、800px 上限、移动端边距、证书、协议、端口、Node 系数、出口和中转弹窗保留。信息图标支持悬停、键盘聚焦/Escape、手机点击。中文、英文、俄文、波斯文标签均有翻译。

默认 `1`，旧安装升级后保持原扣除方式。允许大于 `0`、不超过 `1000`、最多五位小数；不允许 0、负数、布尔值、NaN/Infinity。这是扣除流量的倍率，不限制或提高网速。例如本机业务使用 1 GiB，系数 2 时计入 2 GiB；0.5 时计入 0.5 GiB。示例仅描述输入草稿，点击保存并成功响应才持久化。

数据库保存后，在下一次 `record_user_usages` 采集开始时读取一个系数快照。采集已开始时的保存不影响本批次。尚在 Xray 计数器内、未落库的流量属于下一批次，不能精确按保存时刻划分；已落库的用户用量、管理员总用量、小时用量、网络计数均不重新缩放。

主控本机业务字节先按十进制计算，再对每个用户每批次向下取整到整数字节；小于 1 字节的尾数不累积。用户、管理员与本机小时账本使用同一结果。此轮不改变 Node 既有倍率/取整行为。HWID 凭据先按用户聚合后计费，不改变设备限制。数据库读取/验证失败时，在 reset=True 探测前失败，不用猜测的系数继续采集。

## 中转与实际流量

计费只查询本机业务 Xray API 和已连接/启动的远程 Node API。透明 TCP 中转是独立进程，不进入本机业务用户统计；目标 Node 按其自己的系数扣除，主面板或另一 Node 作为中转来源不会因此再收一次用户流量。中转服务器的网卡、供应商带宽/费用仍会产生实际流量，不能承诺零成本。

`record_node_usages`、系统上传/下载与 Node 网络统计继续记录实际字节，不乘本机系数。使用系数不改变出口 IP、订阅名称/端点、TLS/REALITY 参数，也不能修复公网线路慢的问题。

## API 合同

仅 sudo 管理员，沿用 Bearer token、原 `get_db` 和权限验证；不新增控制端口。

| 接口 | 用途 | 请求与响应 |
| --- | --- | --- |
| `GET /api/node/main/usage` | 读取本机业务系数 | 无请求体；`{"usage_coefficient":1.0}` |
| `PUT /api/node/main/usage` | 独立保存本机业务系数 | `{"usage_coefficient":2.5}`；成功返回持久化后的同结构 |

`200` 成功，`401` 无有效身份，`403` 非 sudo，`422` 缺字段/无效数值/超范围/精度，`503` system 初始化记录缺失；数据库故障按既有服务错误处理，不返回伪成功。前端读取失败禁用保存并提供重试；输入或写入失败保留草稿，不自动改成 1。加载/重复保存受保护。多个 sudo 管理员的写入沿用最后成功提交者生效，不提供乐观锁/历史审计。

原 `GET /api/node/settings` 证书与 min_node_version 响应不变；原远程 Node 增改查与 `usage_coefficient` 字段不变。

## 迁移、配对与升级

新增 additive 迁移 `a123bc45de67`，接 `9012ab34cd56`，只给 `system` 增加非空 `usage_coefficient FLOAT DEFAULT 1.0`。旧记录和新记录默认 1；不删除用户、配置、证书或数据。SQLite 升级/降级保留已有记录有回归；MySQL/PostgreSQL 生产迁移仍需相应环境验收。

只构建/更新 `kissow/Marzban` 主镜像。`kissow/Marzban-node` 和 `kissow/Marzban-scripts` 无运行时/接口/命令变更，本轮不需要配对更新。Xray 固定 `v26.3.27`。既有安装不要重新 install、重复 adopt、删除卷或覆盖 .env。

本轮镜像发布并核对 revision 后，已切换 Fork 的主控用 `marzban update`；备份 `.env`、数据库、证书和配置，维护窗口操作，更新短暂重启主控。脚本已有自动备份不是恢复演练。回滚前备份；额外字段可以被旧 ORM 忽略，但不自动降级数据库或删除用量记录。

## 验收流程与证据

1. 本地 SQLite API/计费/迁移测试，四语言/表单校验/草稿与错误保护，类型/生产构建和 diff/依赖检查。
2. 功能分支 PR；干净 Linux 同一测试命令成功后合并。
3. master 正式 Actions 成功，核对 GHCR latest index、amd64/arm64 manifest/config digest 与运行时 revision，不能引用旧镜像作为本次发布。
4. 主控更新后 GET 默认 1，设置 2/0.5、刷新/重启确认持久化，已落库用量不重算。采集两批次比较本机用户/管理员/小时账本和原 Node 系数；网络统计保持实际字节。恢复到希望的系数。
5. 验收证书/订阅/手机/桌面/直连/主控中转/Node 中转、错误提示与权限。测试用独立账号，不能改变真实用户额度或中断正在使用的节点进行测试。

HTML 提案用原组件和主题，已获用户认可。浏览器自动视觉验证受策略限制未执行，不能用 TS/静态源码检查代替。运行时源码是现有开源 Marzban 结构上的局部修改；本轮未复制第三方新增算法，保留原许可证和上游署名。

本地证据：最终代码全量后端两轮 182/182（固定 Xray 实际进程测试无跳过），本机系数专项 18/18 再连续三轮，前端 54/54（含实际 React/Chakra 四语言 SSR；不等同浏览器视觉验收）、TypeScript/Vite、固定入口 Check、pip check/diff 通过。现有 utcnow/Pydantic 弃用与大 bundle 警告保留，非本轮新增故障。

开发失败复盘：新测试 Node fixture 最初漏填必填端口，补齐 fixture；网络探测 mock 最初误用用户统计结构，改成既有 up/down 合同；原 migration-head 断言需接新 additive head，保留全部旧迁移链断言；Toast onError 不能返回 ToastId，使用 void 回调；增加实际 SSR 后发现缓存初始数值仍为空，改为从已加载 query 初始化草稿并保留后续 dirty 保护。对应 API、原网络统计、迁移链、类型与 SSR 回归已通过。没有隐藏/跳过失败测试。

## 本轮发布证据（2026-10-08）

源提交 `6f65298e1972a5a55df44b2267cc6e8a57807022`；[PR #19](https://github.com/kissow/Marzban/pull/19) 已合入 master。运行时/镜像 revision：`15a11e9d5bdf884fa860456e3a4ae0602d6783b1`。
[PR CI 37777207870](https://github.com/kissow/Marzban/actions/runs/37777207870) 和 [正式构建 37777455474](https://github.com/kissow/Marzban/actions/runs/37777455474) 首次成功。两轮 Linux 普通后端182项中的两项真实 Xray 在普通阶段跳过，然后显式安装固定核心，两项实际进程测试均通过；前端54/54、类型/生产构建通过。未把跳过记录作为真实测试通过。

镜像：`ghcr.io/kissow/marzban:latest`；index：`sha256:ed5d2641733126431104155f62a447390767f524525e7303f5bfc46741cb5f35`。
核对时间：2026-10-08T20:39:05.7344197+08:00；index/manifest/config均按原始字节SHA256核对，核对前后latest未改变；两架构OCI revision均为上面的运行时提交。

| 平台 | manifest digest | config digest |
| --- | --- | --- |
| linux/amd64 | `sha256:48b1bd5652a18cfd7746f526bddc0c7f7ba0ee6e4c292ba56aed4131730bcc48` | `sha256:ebbabd599990ae21df4c3595618f8c17e2267dbd4683b49f2df215e2b90170ea` |
| linux/arm64 | `sha256:25d7dea861a8036e2604f2943daf6df1fa4c46e8b9373227c485efda58097c91` | `sha256:9e21f75c637f1d6a60e2c6cfffec92cbe78e9fa931fcd3391bd3c5f9588de26d` |

GitHub runner 提示 Action Node20切换到Node24及ubuntu-latest后续迁移；本轮均成功，不是构建错误。本轮未升级Action版本或扩大运行时变更。

实际实现组件离线HTML已从同一运行时NodesDialog/MainUsageCard/原主题编译，完整四语言，1153294字节，SHA256 `7f3d90c62e116af42cd6e0633d13d9b0dd210d6f18fb7851b19815f30f3ec5fd`。它使用离线fixture，不更改服务器。实际浏览器截图、手机操作、服务器迁移/容器启动与计费仍待用户验收，不能标为稳定版。

## 服务器 SSH 更新（已切换 Fork）

```sh
marzban update
marzban status
marzban logs --no-follow 2>&1 | tail -n 100
docker ps --filter label=com.docker.compose.service=marzban --format '{{.ID}}' | xargs -r docker inspect --format '{{.Name}} | {{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

预期镜像 `ghcr.io/kissow/marzban:latest`，revision `15a11e9d5bdf884fa860456e3a4ae0602d6783b1`（不要求与后续仅文档提交相同）。更新前备份，下载可能数分钟，短暂重启；不要重装或删卷。Node/scripts本轮不用更新。浏览器刷新后，在节点设置顶部保存本机系数并按前述验收流程确认；本轮没有远程操作用户服务器。

## English summary

The existing Node dialog now includes a separate local main-server billing setting, default 1. Only subsequent collection batches from the local business Xray API are scaled; persisted historical usage, raw network statistics, remote Node multipliers and transparent relay behavior are unchanged. Sudo-only GET/PUT `/api/node/main/usage`; additive migration `a123bc45de67`; range greater than zero through 1000 with up to five decimal places. No Node or deployment-script update is required for this feature. The image above is published and verified, but production server and browser visual acceptance remain pending. Preserve upstream licensing and existing deployment data.
