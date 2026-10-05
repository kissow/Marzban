# MR-DASHBOARD-I18N-MOBILE：多语言与手机设置入站修复

## 范围与原界面保留

直接调整原 React/Chakra 组件，没有另设计主题或表单。原设置入站 ModalBody 固定 440px，而容器使用 fit-content，窄屏仍被内部宽度撑大。现弹窗 `w="440px"`、`maxW="calc(100vw - 24px)"`，内容 `w="full"`、`minW={0}`：桌面仍为 440px，手机左右各留 12px。没有靠全局隐藏横向溢出来掩盖内容。

长入站标题可换行；原高级设置/操作行可换行；9 个原帮助 Popover 限制视口宽高、可纵向滚动，长示例可折行。保留保存/关闭、全部原入站字段、验证行为、协议、端口、证书及主题颜色。

英语、波斯语、简体中文、俄语补全共用标签、占位符、操作说明、状态筛选、在线/到期相对时间及日期选择器。API 无时区的 online_at 按原 UTC 含义解析；时间边界、复数与语言切换有回归。hosts 必填验证在执行验证时读取当前语言，不冻结在初始化语言。协议、Xray、技术示例保留原名。

## 接口与跨仓库兼容

- `GET /api/users`：显示状态翻译，查询仍为 `active/on_hold/disabled/limited/expired`；修复选中值误用 sort 的 UI 问题。
- `GET /api/hosts`、`PUT /api/hosts`：请求、响应、权限、端口转换不变；必填提示仅前端本地化。
- 无新增/删除接口、认证变更、数据库迁移、订阅策略或 HWID/UDP 改动。
- Marzban-node、Marzban-scripts：本轮无代码/协议/命令/镜像变化，无需因本轮更新已配对子节点。
- Xray 正式核心 v26.3.27 不变；不删除用户、数据库、证书或数据卷。
- 修改原项目代码，未借入新外部源码；保留原作者、许可和 Chakra 主题归属。

## 本地验证证据

固定 PowerShell 7 / UTF-8 / 项目内缓存和 Python 环境入口，所有产物在项目 F 盘。

| 检查 | 本轮实际结果 | 边界 |
| --- | --- | --- |
| `npm run test:locales` | 34/34 通过 | 词典键/变量、复数、时间边界、UTC、语言切换、原表单、API 枚举及响应式源代码约束 |
| 固定入口 `-Action Test` | 95/95 通过 | 主控现有完整回归，不等于真实服务器验证 |
| `tsc --noEmit` | 通过 | 类型检查 |
| 固定入口 `-Action Check` | 通过 | 项目解释器依赖与 `git diff --check`，文档补齐后再次检查 |
| 生产 Vite build | 通过 | `.cache/dashboard-i18n-mobile-build`，保留既有大 chunk 提示 |
| 原组件预览 build | 通过 | `.cache/localization-preview-build`，不是视觉验收 |

主控既有 datetime/Pydantic 弃用提示仍存在，本轮不扩展修改后端。没有新增阻断构建错误，不宣称全项目零 BUG。

源代码/计算约束覆盖 320/360/375/390/768/1280px，但尚未证明浏览器实际布局。原组件预览在工作区 `ui-preview/localization-live/`，加载生产 HostsDialog/UsersTable/Filters/Language、主题与样式；只用合成账号/域名，禁止非 fixture API，不调用生产服务器。

## 视觉与发布状态

浏览器工具返回安全策略校验不可用、不能授权访问，因此没有真实手机截图；没有用其他浏览器或伪造 UI 绕过校验。后续允许访问后仍需验证：

1. 320/375/390px 下打开原入站弹窗与高级选项，边缘/字段/按钮/帮助弹层不出屏幕，内容可滚动。
2. 桌面仍为原 440px；浅色/深色主题、保存/关闭、原输入项均保持。
3. 切换 en/fa/zh/ru，核对在线/到期、状态筛选、日历与必填提示；实际 API 状态参数仍为原枚举。
4. 后续仍需展示实际组件效果并完成手机端视觉验收。2026-10-06 用户明确要求“上传仓库，构建，给我服务器更新”，本轮按该授权先发布，未将其登记为视觉验收通过。

2026-10-06 发布前复核：语言回归 34/34、主控 95/95、固定入口 Check、TypeScript、生产 Vite 构建再次通过。按用户明确授权完成提交/推送、合并与镜像发布；服务器未更新/验收，真实视觉验收待完成；旧镜像不作为本轮发布证据。

## 正式发布证据

- 修复源提交：`33081ba100b7c21d652db91e78497c4de447a63d`；分支 Actions [37352009623](https://github.com/kissow/Marzban/actions/runs/37352009623) 成功。
- [PR #11](https://github.com/kissow/Marzban/pull/11) 已合并；master/镜像源 revision：`5655213099c18532ff3daff5cead010c181a19e9`。
- 正式 Actions [37353281396](https://github.com/kissow/Marzban/actions/runs/37353281396) 成功：Linux 后端 95/95、语言 34/34、TypeScript/生产构建、正式核心版本闸门通过。
- 正式镜像：`ghcr.io/kissow/marzban:latest`；index `sha256:793c61738cf18f8641c2ce4b86037a41064903b7e59e4c49a296f8121c2947ce`。
- latest 推送完成日志：`2026-10-05T18:16:26Z`（UTC；香港 2026-10-06）。登记时间采用本地日期，未把 UTC 的 10 月 5 日写成另一次发布。

| 架构 | Manifest digest | Config digest | OCI revision |
| --- | --- | --- | --- |
| linux/amd64 | `sha256:7c1d7aebb9037ff0918d1d305677983097a55c696e8b56c779ecdf5a7c34894f` | `sha256:3b66552f5faf9386c3f4fd1f1f3fd8aefe139078371452190fdd630981d4cf83` | `5655213099c18532ff3daff5cead010c181a19e9` |
| linux/arm64 | `sha256:ca9f1cc579c9a5f8d700d80669e538fe5b35a51b3f985f4ae51bdccbd3cfd1bb` | `sha256:2bfc47defaad8cd94db369de67a5d3ab07e9c170c46c46acb64015b9a8118924` | `5655213099c18532ff3daff5cead010c181a19e9` |

已通过 GHCR 独立读取 index → 双架构 manifest → config，核对原始字节 SHA-256 与描述符匹配、两个 OCI revision 等于合并源、核对前后 latest 不变。首次读取 config 时远端连接短暂断开，重试成功，不视作构建失败。文档证据回写使用 `[skip ci]`；文档提交不是镜像源提交。

GitHub Actions 仍有既有 action Node.js 20 弃用和 ubuntu-latest 未来切换提示，属于构建环境提示；未阻断本次成功发布。既有 datetime/Pydantic 和大 chunk 提示保留，不宣称零 BUG。

## 已切换 Fork 的服务器更新

仅更新主面板，不重复 adopt/install，不改 Node：

```sh
marzban update
marzban status
marzban logs --no-follow 2>&1 | tail -n 100
```

root 无需 sudo。现有 Fork update 脚本先备份环境、compose 与本地数据目录，再拉取/重启；外部数据库仍须单独备份。更新会短暂重启，禁止删卷、重装或覆盖证书/环境文件。

容器名可能是 marzban-1，按服务标签确认本次 revision：

```sh
docker ps --filter label=com.docker.compose.service=marzban --format '{{.ID}}' |
  xargs -r docker inspect --format '{{.Name}} | {{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

预期 revision 为上表 `5655213099c18532ff3daff5cead010c181a19e9`。若不同，先核对 compose 镜像和更新日志，不宣称成功。服务器/视觉验收按前述四项检查；本轮尚未执行，镜像发布不等于验收通过。
