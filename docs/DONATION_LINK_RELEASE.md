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
- 源提交：`e72943b6dad1abf6ccd58307cb1008bd6793d81f`，已推送 `kissow/Marzban` 的 master，并通过 GitHub API 核对远程提交。
- Actions：[37123809995](https://github.com/kissow/Marzban/actions/runs/37123809995)，workflow `build.yml`，首次运行成功，后端/前端检查、固定核心闸门、多架构构建和 GHCR 发布全部通过。
- GHCR `ghcr.io/kissow/marzban:latest` index：`sha256:28ffe73996bd0078df894e0d56b0ec742087d678acebd8c8d34b646791f7eb6c`。
- Linux amd64：`sha256:c9eae7386c4155fc3c2de9cee8032c5360a2fe858bd8fcf2dbd5b7826bca6459`；Linux arm64：`sha256:bcc8d796faacd77d4dba3f5784862f812e72de6db7d0e566a2ded933def8695d`。
- 2026-10-03 通过匿名 GHCR manifest/config 读取核对两个架构，OCI revision 均为 `e72943b6dad1abf6ccd58307cb1008bd6793d81f`；新镜像确实对应本次源修改。后续文档提交使用 `[skip ci]`，不改变镜像源 SHA。
- 构建仅出现 runner 的 Node.js 20 弃用/强制运行 Node.js 24 与 ubuntu-latest 未来迁移提示，不是失败；未修改产品依赖或核心。
- 服务器点击验收：待维护者更新后确认；这不是已通过的服务器验收。

## 已切换 Fork 的服务器更新

完成现有数据备份后，在主面板服务器的 root SSH 运行：

```bash
marzban update
marzban status
```

更新的是主面板，不需要重复 adopt/install，不需要更新 Node。已核对仓库更新脚本会先备份，再 pull 与 up 主面板服务；保留已有 .env/数据卷/证书/端口。更新后刷新或强制刷新面板，点击捐赠，目标应为 `https://github.com/kissow/Marzban#donation`。这里只提供命令，未远程执行生产服务器更新。
