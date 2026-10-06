# MR-20261007-BROWSER-TRANSLATION：浏览器翻译 DOM 兼容

维护者 Mr.shaw。状态：本地修复与验证；未推送、未运行本轮 Actions、未发布新镜像、未进行服务器验收。已有 latest 不包含本地修改。

2026-10-07 用户已授权推送线上仓库和构建新主控镜像。发布后回写 PR、Actions、提交与双架构镜像证据；服务器更新及真实翻译服务验收仍待用户执行。

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
- Marzban：仅前端兼容与回归闸门，需要未来新主控镜像。
- Marzban-node、Marzban-scripts：运行时、协议、安装/更新命令无变化，不需要本轮构建或服务器更新。

## 本地测试

- 既有语言 34 项与新增保护/生产 JSX 6 项：40/40；TypeScript --noEmit、生产构建通过，保留已有 Vite 大 chunk 提示。
- 固定项目入口完整后端回归 116/116，Check/git diff --check 通过；已有 UTC/Pydantic 弃用提示保留，后端未修改。
- 新增测试同时进入 master 构建与 PR 检查；验证 html/body/元信息、生产动态 JSX 包装、四语言文本和没有全局 DOM monkey patch。
- 原 HostsDialog/Chakra 组件在本地 Edge 无头浏览器渲染：强制替换 span 内文本为 font 包装后，加载/空列表到现有入站的切换与关闭/重开每轮 10 次，连续两轮通过；无 pageerror/removeChild，四语言切换通过。1280px/390px 宽度断言与展开入站截图核对通过，不使用重新设计的示意图。截图在工作区 ui-preview/browser-translation-1280.png、browser-translation-390.png；测试入口 .cache/verification/test-browser-translation.cjs 只留本地，项目缓存/预览不加入发布提交。
- 这是本地模拟外部翻译 DOM 改写，不是实际 Chrome/Edge 翻译服务或线上服务器验收。测试首次因 Vite 测试路由挂载顺序错误超时，修正测试中间件后通过；未把失败计为产品通过。
- 原组件开发模式仍有已有的 button 内嵌 button 警告，和本次翻译卸载错误不同；不改用户未要求的原交互结构。Vite 大 chunk、上述非致命警告保留记录，不宣称全项目无问题。

## 发布与验收（未执行）

用户授权后推送、运行干净 Linux CI、构建主控镜像并核对两架构摘要/revision；服务器既有 Fork 使用 marzban update，不重装、不删除卷。发布后重新加载页面，用原语言菜单选择中文，反复打开/关闭主机设置及展开入站，核对加载、空列表、现有列表和四种语言；验证手机宽度、正常保存/协议字段及无 removeChild 异常。Node 无需更新。浏览器自己的强制翻译兼容仍须在用户实际浏览器验收。
