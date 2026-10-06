# MR-20261007-BROWSER-TRANSLATION：浏览器翻译 DOM 兼容

维护者 Mr.shaw。状态：修复已上传、PR Linux CI 通过并合入主分支；正式镜像构建成功，latest 双架构 manifest/config/OCI revision 已核对；服务器更新与实际翻译服务验收未执行。镜像发布不等于服务器已部署或通过。

2026-10-07 已按用户授权推送线上仓库和构建新主控镜像，PR、Actions、提交与双架构镜像证据已回写；服务器更新及真实翻译服务验收仍待用户执行。

## 原因和源码依据

用户确认关闭浏览器翻译后，主机设置/入站弹窗恢复正常。这里的 Node 是浏览器 DOM 元素，不是 Marzban-Node。HostsDialog 的加载和无入站状态此前直接输出条件文本；翻译工具替换 React 管理的文本节点后，React 再移除旧节点会遇到 NotFoundError/removeChild。

参考 [React issue #11538](https://github.com/facebook/react/issues/11538) 与 [HTML translate 属性规范](https://html.spec.whatwg.org/multipage/dom.html#the-translate-attribute)。本轮自行在原组件实现兼容保护，没有复制第三方补丁代码；保留上游许可证和致谢。

## 修复与边界

1. 原 index.html 的 html/body 使用 translate=no 和 notranslate，head 使用 Google opt-out；声明在 React 加载之前生效，body 同时覆盖挂载到 root 外的 Chakra Modal/Popover Portal。
2. HostsDialog 原加载/无入站文本使用 Text as=span；翻译替换 span 内部文字后，状态切换删除的是 React 保留的 span 外壳，不直接删除已经被替换的文本节点。
3. 原生 i18next en/zh/fa/ru 菜单继续可用，原主题、宽度、控件、协议、证书、端口、数据均保留。没有修改语言检测或用户此前未提交的语言代码。
4. 不改写 Node.prototype.removeChild/insertBefore，不吞掉其它真实 DOM 错误。翻译声明不是权限边界：强制改写整个元素、忽略 translate=no 的第三方扩展仍可能破坏页面；无法保证所有扩展兼容。受支持的语言切换方式是面板菜单。
5. 本修复对新加载的文档生效；已经被翻译破坏的旧标签页不能靠声明自动修复，升级后需要重新加载页面。

## API 和三仓库兼容

- GET /api/hosts、PUT /api/hosts、GET /api/inbounds 请求、响应、认证和副作用均不变；无新增/删除接口或字段。
- 数据库/订阅/认证/设备策略/HWID/UDP 不变；正式 Xray 保持 v26.3.27。
- Marzban：仅前端兼容与回归闸门，新主控镜像已发布，需要更新主控服务器。
- Marzban-node、Marzban-scripts：运行时、协议、安装/更新命令无变化，不需要本轮构建或服务器更新。

## 本地测试

- 既有语言 34 项与新增保护/生产 JSX 6 项：40/40；TypeScript --noEmit、生产构建通过，保留已有 Vite 大 chunk 提示。
- 固定项目入口完整后端回归 116/116，Check/git diff --check 通过；已有 UTC/Pydantic 弃用提示保留，后端未修改。
- 新增测试同时进入 master 构建与 PR 检查；验证 html/body/元信息、生产动态 JSX 包装、四语言文本和没有全局 DOM monkey patch。
- 原 HostsDialog/Chakra 组件在本地 Edge 无头浏览器渲染：强制替换 span 内文本为 font 包装后，加载/空列表到现有入站的切换与关闭/重开每轮 10 次，连续两轮通过；无 pageerror/removeChild，四语言切换通过。1280px/390px 宽度断言与展开入站截图核对通过，不使用重新设计的示意图。截图在工作区 ui-preview/browser-translation-1280.png、browser-translation-390.png；测试入口 .cache/verification/test-browser-translation.cjs 只留本地，项目缓存/预览不加入发布提交。
- 这是本地模拟外部翻译 DOM 改写，不是实际 Chrome/Edge 翻译服务或线上服务器验收。测试首次因 Vite 测试路由挂载顺序错误超时，修正测试中间件后通过；未把失败计为产品通过。
- 原组件开发模式仍有已有的 button 内嵌 button 警告，和本次翻译卸载错误不同；不改用户未要求的原交互结构。Vite 大 chunk、上述非致命警告保留记录，不宣称全项目无问题。

## 代码、CI 与已核验镜像（2026-10-07）

- 源提交：7a0db490577e470f1366f807335152e63a6f456d；[PR #14](https://github.com/kissow/Marzban/pull/14) 已合并。
- PR CI：[37494129629](https://github.com/kissow/Marzban/actions/runs/37494129629) 成功；干净 Linux 后端 116/116、前端 40/40、类型/生产构建通过。
- 主分支运行时提交：9659956325e9cb8c39ec36ee6e34e4119f0c6660；正式构建 [37494615636](https://github.com/kissow/Marzban/actions/runs/37494615636) 成功，状态更新时间 2026-10-06T16:25:15Z（香港 2026-10-07 00:25:15）；Linux 116/116、40/40、类型、生产构建、Xray pin 与镜像发布全部通过。
- 镜像 ghcr.io/kissow/marzban:latest；index sha256:6838f71ea0e3b97baa1cb217bb83d1f0b1acbb63466fe1e1863a2130220c2d45。
- linux/amd64 manifest sha256:ebbe138b8230e971b31b84b9184cc4db8a0c43f0285aaafe9e6a7cea256cf62b；config sha256:094bf9a4feb906cd8825781ecc73bf5e8b36fe08b64908169eea3bb1dc287430。
- linux/arm64 manifest sha256:fa93f84b22945bf4f5871f419f510c575958a187f86f90ce4a52fb1f2b08d66f；config sha256:4a8c8bf71d622984c5da042b43525a202ec2b0d753a7632e5c4c618058bd26a1。
- 2026-10-07T00:26:02+08:00 已校验 index/manifest/config 原始字节 SHA256 与声明一致；两架构 OCI revision 均匹配 9659956325e9cb8c39ec36ee6e34e4119f0c6660，核验前后 latest 未变化。
- 发布证据回写仅文档 [skip ci]，不触发重复构建；后续文档 SHA 不应当作运行时 revision。
- Git HTTPS 传输再现 connection reset；通过 GitHub API 上传，所有 12 个文件的 blob、tree 和 commit SHA 与本地对象一致后才创建 PR。原有语言改动、AGENTS、缓存和预览均未上传。
- Actions 提示旧 actions 的 Node.js 20 运行时迁移和 ubuntu-latest 后续迁移；本次检查成功，这些平台维护提示与翻译 DOM 异常不同，不宣称已处理。

## 服务器验收（未执行）

已切换 Fork 的主控服务器执行以下 SSH 命令，保留更新脚本的升级前备份；不重装、不删除卷、不覆盖 .env。镜像拉取可能数分钟，更新会短暂重启。

```sh
marzban update
marzban status
marzban logs --no-follow 2>&1 | tail -n 100
docker ps --filter label=com.docker.compose.service=marzban --format '{{.ID}}' | xargs -r docker inspect --format '{{.Name}} | {{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

期望 ghcr.io/kissow/marzban:latest，运行 revision 为 9659956325e9cb8c39ec36ee6e34e4119f0c6660。发布后重新加载页面（桌面 Ctrl+F5），用原语言菜单选择中文，反复打开/关闭主机设置及展开入站，核对加载、空列表、现有列表和四种语言；验证手机宽度、正常保存/协议字段及无 removeChild 异常。Node 无需更新。浏览器自己的强制翻译兼容仍须在用户实际浏览器验收。当前没有远程执行服务器更新或验收，不标记稳定发布。
