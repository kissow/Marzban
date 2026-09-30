# Mr.shaw Marzban Fork 更新记录

本文件仅记录本 Fork 相对 [Gozargah/Marzban](https://github.com/Gozargah/Marzban) 的改动。原作者、许可证和上游 Git 历史均保留；完整功能边界见 [FORK_FEATURES.md](FORK_FEATURES.md)。

## mrshaw-v0.8.4-preview.1（2026-09-30，预览版）

- 节点设置弹窗改为最大约 1360px 的响应式宽版，保留原有证书、端口、启用开关、保存和删除等官方 Chakra 界面功能。
- 节点运行状态显示 CPU、内存、磁盘、运行时间、活跃用户五项；宽屏五列、手机端两列。没有可靠节点级来源时，活跃用户显示不可用，不虚构数量。
- 本地前端构建已通过；真实 Linux Node、Xray 和测试数据库迁移仍需验收，暂不建议直接用于生产环境。

## 开发中（尚未稳定发布）

- 节点设置沿用官方 Chakra 界面与证书、端口、启用开关等原功能，新增按节点折叠展示的运行状态。
- 新增受管理员权限保护的 `GET /api/node/{node_id}/health`，通过原有认证通道读取该节点的 CPU、内存、磁盘、运行时间；无可靠来源的在线设备数返回空值。
- 每个 Marzban-Node 可独立保存一条 HTTP 或 SOCKS5 住宅 IP 出口。支持服务器、端口、可选账号密码；密码加密存储，API 不回显明文。
- 保存出口时只向对应 Node 下发配置，旧版 Node 不支持扩展时拒绝保存；删除出口后恢复原有路由。
- 设备数量限制尚未实现，计划在用户设置区域单独开发，不能把公网 IP 数当作实际设备数。

发布时须记录与 `kissow/Marzban-node` 的配对版本，并完成真实 Xray、Linux Node 与数据迁移测试。
