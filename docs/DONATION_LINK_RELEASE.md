# MR-20261003-DONATION-LINK 发布记录

日期：2026-10-03。维护者在本地提供新的捐赠目标与钱包地址，并确认修改完成后授权同步仓库。

## 变更与兼容性

- 前端 `app/dashboard/src/constants/Project.ts` 的 `DONATION_URL` 改为 `https://github.com/kissow/Marzban#donation`；原 Header 点击行为、Chakra 主题、宽度及手机布局保持原样。
- 中英文 README 对齐两组 USDT 地址，BNB Smart Chain 的网络名称使用 BEP20；注明支持 Mr.shaw 社区 Fork，同时保留上游项目署名、捐赠参考和许可证。
- 地址仅按维护者提供内容同步，未进行链上归属、有效到账或转账验证；不能将前端构建成功解释为收款验证成功。
- API、数据库、订阅、Node 通道、认证、证书、端口、环境、数据卷和 Xray v26.3.27 无变化。Node/scripts 均无变化、不需要配对构建或服务器更新。
- 回退只需恢复原捐赠常量/README 或使用先前主面板镜像；无需回退数据库或删除数据卷。

## 分阶段证据

- 本地差异检查：`git diff --check` 通过；只包含捐赠常量/说明和本次文档，不提交原有 untracked 文件或缓存。
- 主面板完整后端 unittest 54 项、TypeScript noEmit、Vite 生产构建：通过；保留既有依赖弃用提示和 Vite 大包警告，无错误。
- 构建产物捐赠目标检查：生产 JS 包包含 Fork 捐赠地址且不含旧菜单目标；中英文 README 两组地址一致。
- 源提交与 GitHub 推送：待完成。
- Actions：待完成。
- GHCR latest index/amd64/arm64 digest 与 OCI revision：待完成；旧功能证据不能代替本次构建。
- 服务器点击验收：待维护者更新后确认；这不是已通过的服务器验收。
