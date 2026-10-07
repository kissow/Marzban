# MR-20261008-NODE-RELAY-SOURCES 配对发布证据

状态：主控与Node代码已合并、干净Linux CI和两套latest镜像发布完成；manifest/config字节SHA256和OCI revision已核对，校验前后latest一致。真实服务器/原组件UI/多引擎数据库验收待完成，不标稳定版。文档回写[skip ci]不重新构建，不能用文档提交替代以下运行时revision。

| 仓库 | 源提交 | PR | 合并/镜像revision | 正式Actions |
| --- | --- | --- | --- | --- |
| Marzban | f79598943303fc3884f36920834db3ae8bc21b92 | [17](https://github.com/kissow/Marzban/pull/17) | 93bfbb5b17dd8ee731449976df1a4af4e0f57ca5 | [37657985804](https://github.com/kissow/Marzban/actions/runs/37657985804) |
| Node | fd651365176fa8a0704973576f39585681815231 | [3](https://github.com/kissow/Marzban-node/pull/3) | 7b45fc0dc3b4451045a06123b52ccdaaa5911b8d | [37657976968](https://github.com/kissow/Marzban-node/actions/runs/37657976968) |
| Scripts | 174e357716804a95e3a8fbf74bdf4b632a11c767 | [1](https://github.com/kissow/Marzban-scripts/pull/1) | ed274ba82410f9e6f580cbec59b2a15a89ab81ea（文档） | [37657994843](https://github.com/kissow/Marzban-scripts/actions/runs/37657994843) |

PR CI：主控37656957936/37656958582、Node37657534552、scripts37657579664（分支37657210158），均成功。主控完整发现164项，其中2项外部Xray需后续显式步骤执行，真实固定Xray2/2、前端47/47及类型/构建通过。Node第一轮发现60项跳过8项外部实测，第二轮准备v26.3.27后60/60无跳过。本地及独立发布副本再次164/164、60/60、47/47通过，不把共享本地环境当干净LinuxCI。

## 镜像原始证据
```json
{
  "panel": {
    "revision": "93bfbb5b17dd8ee731449976df1a4af4e0f57ca5",
    "image": "ghcr.io/kissow/marzban:latest",
    "platforms": [
      {
        "platform": "linux/amd64",
        "revision": "93bfbb5b17dd8ee731449976df1a4af4e0f57ca5",
        "digest": "sha256:e21f523a13d34c1de8386fdc9fb93ac73853b9341ac9f814babb1c601bb4a2f6",
        "configDigest": "sha256:35718a9f599531c0cd46535cab4032490f35ed02eff0a8e9c9dc7cd2fafa7871"
      },
      {
        "platform": "linux/arm64",
        "revision": "93bfbb5b17dd8ee731449976df1a4af4e0f57ca5",
        "digest": "sha256:931feb4a22e4dea433174cb5c47b9af11515b919abb0fcd161b202799e5945aa",
        "configDigest": "sha256:7cd6ebbdf7d0d37d2197fc3da2c30bc6804f72b9dc31239236d2a9644c5100de"
      }
    ],
    "indexDigest": "sha256:2d62789d0db0350b999cd41e2f1bc86f1388b1b67c5b6466c339054b8c3c6408",
    "checkedAt": "2026-10-08T01:33:03.19829+08:00"
  },
  "node": {
    "revision": "7b45fc0dc3b4451045a06123b52ccdaaa5911b8d",
    "checkedAt": "2026-10-08T01:27:14.3093771+08:00",
    "platforms": [
      {
        "configDigest": "sha256:cc397653ee77fe26aee01ec3643761b90ced85e2cba7662eac9af4a007d41f60",
        "revision": "7b45fc0dc3b4451045a06123b52ccdaaa5911b8d",
        "digest": "sha256:30e0928e2b3fc35773d224464b4f27c9cc5b4d874e425b194769cd9e9f62af9e",
        "platform": "linux/amd64"
      },
      {
        "configDigest": "sha256:2287ceb4bdbc0ae70ae0dad24e848caee1cd08a0c740478809f4e4b75e716466",
        "revision": "7b45fc0dc3b4451045a06123b52ccdaaa5911b8d",
        "digest": "sha256:3025e572311841f27ecd6e00532f4dea68da4c171bf307971fa2e33a6cf0c216",
        "platform": "linux/arm64"
      }
    ],
    "image": "ghcr.io/kissow/marzban-node:latest",
    "indexDigest": "sha256:752c9ac1ad65934f4b6ec26e5061128f6ca6db424c6c93143a83bb1affb00129"
  }
}
```

## 合同与范围

[完整管理API/认证/错误/来源迁移/升级回滚](NODE_RELAY_SOURCES.md)、[原Host匹配与订阅兼容](NODE_RELAY_SUBSCRIPTION.md)、[Node REST/RPyC线协议](https://github.com/kissow/Marzban-node/blob/master/docs/node-relay.md)。首版仅VLESS TCP/RAW REALITY、IPv4/DNS-only入口、单跳来源选择；源使用镜像已有Xray独立进程透明TCP转发，目标继续原认证/设备凭据/出口。来源完整快照更新可能短暂影响同源其它中转会话，不是零中断或任意UDP转发。

## SSH升级与新安装

已有Fork先备份，在承担来源的Node执行：

```sh
marzban-node update
marzban-node status
docker inspect marzban-node --format '{{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

然后主控服务器：

```sh
marzban update
marzban status
marzban logs --no-follow 2>&1 | tail -n 100
docker ps --filter label=com.docker.compose.service=marzban --format '{{.ID}}' | xargs -r docker inspect --format '{{.Config.Image}} | {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

新Node服务器继续原一键安装，会拉取本仓库新latest：

```sh
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban-node.sh)" @ install
```

仅新服务器用install；已有Fork不重复adopt、不重装/删卷。新Node仍需主控提供的原客户端证书、与面板一致的原控制/API端口。中转来源/业务入口由主控管理，源安全组放行业务TCP端口。固定核心26.3.27、证书、用户/.env/卷不改；更新脚本保留数据并备份。实际更新前记录备份，后检查准确镜像revision、Node能力/连接、核心，刷新订阅。仅作目标的既有配对Node不因来源功能强制更新。

## 服务器验收与测速

1. 刷新订阅：原别名/数量/顺序不变，无额外Relay；开启时对应端点改为所选源，关闭恢复原目标。客户端旧项按其更新规则清理。
2. 同一客户端/目的地分别测目标直连、主控来源、Node来源，记录时段、出口IP、延迟、下载/上传及失败率；不要同时跑VPS基准影响用户，也不要比较不同测速目的地。
3. 源原直连出口仍为源，中转出口仍为目标（有住宅出口则依目标配置）。至少两个目标、桌面/手机和持续30分钟访问/计费验收；速度受客户到源、源到目标、目标出口最慢段限制。
4. 切换/关闭清理旧监听，源重连/目标停止/占用/失败恢复有真实原因；ACK不等于公网验收，200配置测试不等于并发压测。实际mTLS跨服务器、PostgreSQL/MySQL迁移、UI截图及吞吐仍待验收。

## 工具问题与闸门

正常Git push返回500，连接器写blob返回403 integration权限，未改变权限。旧CLI标准输入与byte-array请求失败，JSON文本请求验证成功；使用现有授权身份的官方Git Data API，严格匹配本地blob/tree/commit SHA后才创建分支/PR，不强推master。空PR数组及并行同分支曾导致辅助脚本422，核对相同SHA后复用，只有上述三个唯一PR。这是发布辅助工具问题，不是产品验证证据。

PR只进行Linux验证、不发布latest；master合并后才构建两架构。保留既有utcnow/Pydantic/Vite chunk及Actions运行器升级提示。实际UI因浏览器策略blocked，未绕过。感谢Marzban/Marzban-Node/Xray原作者与贡献者，许可/历史保留，本轮无3X-UI源码复制。
