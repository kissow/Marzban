# MR-20261003-EGRESS-UDP 发布证据

日期：2026-10-03。作者：Mr.shaw。状态：代码与配对镜像已发布，服务器/实际手机/供应商/UI 截图验收待完成，未标记为稳定版。

## 配对源提交与 Actions

| 仓库 | 镜像源提交 | 成功 Actions |
| --- | --- | --- |
| kissow/Marzban | `10f46df8e52ad24c79a1d4a1aafc020a7f7ad335` | [37119086192](https://github.com/kissow/Marzban/actions/runs/37119086192) |
| kissow/Marzban-node | `ff3ed8affb43a7c0be84b7404b25ba149cd9c805` | [37119086117](https://github.com/kissow/Marzban-node/actions/runs/37119086117) |
| kissow/Marzban-scripts（仅配对文档） | `23c6dffe006eea30e117ffc86972f5fc94eab33d` | [37119329541](https://github.com/kissow/Marzban-scripts/actions/runs/37119329541) |

两边本地完整测试为主面板 54 项、Node 48 项；Linux Actions 后端/前端检查与固定核心实测成功，两个多架构镜像成功发布。本轮 Actions 无失败重跑。发布核验脚本初次将 PowerShell 的 HTTP Byte[] 当作 JSON 字符串，造成架构数量校验失败；改为 UTF-8 解码后重新直接查询 GHCR 成功，此问题只属于本地证据工具，不是产品或 Actions 失败。

## GHCR latest 实测摘要

主面板 `ghcr.io/kissow/marzban:latest`：

- index：`sha256:6d008568b64fc0ebdf6b323d0a3a7ffeb8d717aa55fd93c30724127ff6146a81`
- linux/amd64：`sha256:1206e3f858795ec1790e7506d27c8069e6e72d8a1268369453258647a83f59c9`
- linux/arm64：`sha256:18c54440017bee8aeb3fb0b53e9eb2103806009663c972b2ad8413cfaf399976`
- 两架构 OCI revision 均等于主面板镜像源提交。

Node `ghcr.io/kissow/marzban-node:latest`：

- index：`sha256:01935b08bacfad38f1e938d6edcd675ba44b5a4e89a0fa85be89197b81318cb9`
- linux/amd64：`sha256:b996deaaecea716394623eaeb328bbeabef02da00f6ba15d6efce6200094250a`
- linux/arm64：`sha256:6649c8d399d81b615b87ad69886f0629d34e6150b2dd344bb83c846947e89dc6`
- 两架构 OCI revision 均等于 Node 镜像源提交。

后续仅补发布证据的文档提交使用 `[skip ci]`，不重建镜像；仓库文档 HEAD 可以晚于镜像源 SHA，以本表和 OCI revision 为准，不能把文档 SHA 冒充镜像源 SHA。

## 更新与验收

已切换 Fork 的服务器，备份核对后先在每台 Node 运行 `marzban-node update`、`marzban-node status`，检查主面板连接，再在主面板运行 `marzban update`、`marzban status`。root 不必加 sudo，非 root 使用 sudo。不重复 adopt/reinstall，不删除卷或原数据库、环境文件、证书、配置。脚本运行时无变化；核心仍固定 `v26.3.27`。

旧数据默认 `legacy`，新模式要求 `managed-outbounds-udp-v1`。只为测试 Node 开启新模式；`tcp_only` 不是任意 UDP 转 TCP，也不保证所有软件或实际供应商 TCP53 可用。自定义 DNS 上游替换、既有显式路由优先及非 DNS UDP 阻断的边界见 [功能合同](NODE_EGRESS_UDP.md)。不改变 HWID 策略。

仍待验收：真实 Linux 主面板/Node 认证联调、实际供应商 TCP53、同节点 v2rayNG/Clash Meta DNS/路由对照、住宅出口 IP、非 DNS UDP 应用、UDP 供应商回归、legacy 回退、真实桌面/手机 UI 截图。不得把镜像发布或模拟 TCP DNS 通过当作手机故障已消失的证据。回退前先还原 legacy，使用更新前备份和镜像摘要，不删除数据。
