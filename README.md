## MR-20261008-NODE-RELAY-SOURCES（本地开发，未发布）

连接方式改为原Chakra独立管理弹窗；信息图标悬停/键盘/手机点击说明，四语言补齐。新增主服务器或源Node中转到目标Node，原订阅别名/数量保留，不新增Relay条目。来源切换清理旧监听；自转发/环路/端口占用、能力/完整ACK和失败回滚校验；保存仅应用受影响来源，不被无关离线来源拖住。目标认证/出口保持，固定Xray v26.3.27，证书/控制API端口/用户数据不改。

管理API增加source=main/node、source_node_id、options来源列表；additive迁移9012ab34cd56保持旧行main。Node新增managed-node-relay-v1与原认证REST/RPyC快照，需配对发布并先更新承担来源的Node；仅作目标的既有配对Node不强制更新。scripts运行时代码不变、配对文档更新。

本轮仍未提交推送、Linux CI/新镜像/服务器验收待执行，不能执行update取得尚未发布的功能。原组件实际截图被浏览器安全策略阻断，不用静态检查代替视觉验收。[完整接口、协议、范围、升级和回滚](docs/NODE_RELAY_SOURCES.md)。下方2026-10-07“Node→Node未实现/Node无需更新”只属于当时阶段。

> **MR-20261007-RELAY-INTERNAL-SUBSCRIPTION (local fix; NOT published):** Keep original subscription aliases, order and entry count; switch only the matched Node address/port, never append `(Relay)`. Stored Hosts, credentials and forwarding runtime remain unchanged. Reject unmatched/ambiguous targets; preserve short IDs on the output copy. Backend 149/149 passed twice including pinned-Xray process tests; frontend 45/45, type/build, dependency and diff checks passed. Node/scripts need no update. Node-to-Node is a future extension, not supported in this release. [Contract and pending publication/acceptance](docs/NODE_RELAY_SUBSCRIPTION.md).

> **MR-20261007-NODE-RELAY (image published; server/visual acceptance pending):** Optional per-Node main-server TCP relay for VLESS TCP/RAW REALITY, preserving direct entries and original credentials/certificates/Node controls. Additive migration and four sudo APIs; Node/scripts need no runtime update, Xray stays v26.3.27. PR #16 merged as d23502030358930592016f9ff2f7d3f42acad4e7; Actions 37637973415 succeeded including real pinned-Xray Linux forwarding/recovery. Backend regressions and frontend 44/44/type/build passed; latest amd64/arm64 manifests/configs/OCI revisions verified. Adopted main servers use marzban update, configure the relay, allow its business TCP port and refresh client subscriptions. UI screenshot review remains blocked by managed browser policy; public REALITY/client/speed acceptance pending. [Exact image evidence, setup, API, limitations, rollback and speed tests](docs/NODE_RELAY.md). Documentation-only [skip ci] evidence commits do not replace the runtime image revision.

> **MR-20261007-BROWSER-TRANSLATION (image published; server acceptance pending):** The dashboard opts out of external browser translation; native en/zh/fa/ru language switching is preserved. Existing Hosts loading/empty text uses stable element wrappers to prevent translator-induced React `removeChild` failures. PR #14 merged as `96599563`; Actions `37494615636` succeeded (116 backend/40 frontend tests), and latest amd64/arm64 manifests/configs/OCI revisions were verified. Theme, form layout, protocols, API, data and Node/scripts are unchanged. Existing Fork installations use `marzban update` then reload the dashboard; paired Nodes need no update. [Exact image evidence, root cause, regression and acceptance boundaries](docs/BROWSER_TRANSLATION.md). Documentation-only evidence commits do not replace this runtime image revision.

> **MR-20261006-CONTROL-RESILIENCE (image published; server acceptance pending):** Preserve authenticated Node sessions on transient timeouts, avoid blind core restarts, tolerate slow TLS/control stages, and isolate health/account/usage probes. Final backend suite passed twice (116/116 each); transport/resilience suites passed three further rounds (13/13 and 20/20 each). PR #12 merged as `eb43761e`; Actions `37486719383` succeeded, and both latest architecture digests/OCI revisions were verified. No new API/schema/UI/certificate/port/HWID/Xray/Node/scripts changes. Already adopted installations use `marzban update`; paired Nodes need no update for this fix. [Exact image digests, retry contracts, update commands and server acceptance](docs/NODE_CONTROL_RESILIENCE.md). Publication is not proof of server deployment or stable public-network connectivity; older evidence below remains historical.

> **MR-DASHBOARD-I18N-MOBILE (image published; server/visual acceptance pending):** Complete shared labels, relative online/expiry times and calendars across en/fa/zh/ru. The original Hosts dialog remains 440px on desktop and fits the mobile viewport; long titles and help wrap. PR #11 merged as `56552130`; Actions `37353281396` succeeded, and both latest architecture digests/OCI revisions were verified. Locale regressions 34/34, backend regressions 95/95, TypeScript and production builds passed locally and in Linux CI. No API/schema/Node/scripts/Xray changes; paired Nodes need no update. Real mobile visual and server acceptance remain pending. [Exact image digests, scope and update instructions](docs/DASHBOARD_I18N_MOBILE.md). The release summaries below are historical, not this latest image's source or digest.

> **Node recovery (image published; server acceptance pending):** Per-node lifecycle serialization, isolated health recovery, stage-specific errors, bounded TLS handshakes and safe retry handling address connection risks. Two complete 95/95 local runs and Linux CI passed. PR #10 merged as `122632c8`; Actions `37340574125` succeeded and both `ghcr.io/kissow/marzban:latest` architectures have the matching OCI revision. No UI/API/schema/Node wire-protocol/Xray changes; already paired Nodes and scripts need no update. [Verified image digests, scope, API semantics and server acceptance gates](docs/NODE_RECOVERY_RELEASE.md). Server deployment and real-network acceptance have not been performed for this release.

> **Node connection / scheduler maintenance (2026-10-03, image published; server acceptance pending):** Establish the existing authenticated Node session before the non-legacy egress health check; preserve the failure reason. Pin APScheduler 3.11.3 without the deprecated pkg_resources import. Local/Linux CI 69/69 and dashboard checks passed; source `78e7b8e`, Actions `37135175798`, both latest architectures and OCI revisions verified. No API/schema/UI/certificate/port/HWID/Xray changes; already paired Nodes and scripts need no new update. [Compatibility, tests and release evidence](docs/NODE_CONNECTION_RELEASE.md). The image records below describe earlier releases.

<p align="center">
  <a href="https://github.com/gozargah/marzban" target="_blank" rel="noopener noreferrer">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Gozargah/Marzban-docs/raw/master/screenshots/logo-dark.png">
      <img width="160" height="160" src="https://github.com/Gozargah/Marzban-docs/raw/master/screenshots/logo-light.png">
    </picture>
  </a>
</p>

> **Historical release (2026-10-03, HWID compatibility):** Source commit `37bab0b113c44ccb2a9db6230ac982b7d2a889a1`, Actions `37090609233`, image index `sha256:c4bbe88b5b547bbdca3d6b8a4bf1e7c92aeb29ae50b36cd758b7c6eccae2edfc`. This is historical evidence, not the current latest digest.

> **Latest panel image (2026-10-03, MR-20261003-DONATION-LINK):** Donation menu now targets this Fork; source `e72943b6dad1abf6ccd58307cb1008bd6793d81f`, Actions `37123809995` succeeded, latest index `sha256:28ffe73996bd0078df894e0d56b0ec742087d678acebd8c8d34b646791f7eb6c`. Both architecture revisions verified. [Publication evidence and update instructions](docs/DONATION_LINK_RELEASE.md). Node/scripts, API, database, certificates, ports and Xray v26.3.27 are unchanged. Server click acceptance remains pending. The following UDP record describes the preceding paired feature release, not the current panel digest.

> **Current release (2026-10-03, MR-20261003-EGRESS-UDP):** Paired panel/Node code and multiarchitecture latest images are published and OCI revisions verified. [Source SHAs, successful Actions and exact image digests](docs/EGRESS_UDP_RELEASE.md). Server/provider/mobile/UI screenshot acceptance remains pending; this is not a stable-release claim. Legacy remains the default; nonlegacy requires the paired Node capability. Scripts runtime and pinned Xray v26.3.27 are unchanged. [Contract, DNS/routing limits and acceptance](docs/NODE_EGRESS_UDP.md).

<h1 align="center"/>Marzban</h1>

<p align="center">
    Unified GUI Censorship Resistant Solution Powered by <a href="https://github.com/XTLS/Xray-core">Xray</a>
</p>

<br/>
<p align="center">
    <a href="#">
        <img src="https://img.shields.io/github/actions/workflow/status/gozargah/marzban/build.yml?style=flat-square" />
    </a>
    <a href="https://hub.docker.com/r/gozargah/marzban" target="_blank">
        <img src="https://img.shields.io/docker/pulls/gozargah/marzban?style=flat-square&logo=docker" />
    </a>
    <a href="#">
        <img src="https://img.shields.io/github/license/gozargah/marzban?style=flat-square" />
    </a>
    <a href="https://t.me/gozargah_marzban" target="_blank">
        <img src="https://img.shields.io/badge/telegram-group-blue?style=flat-square&logo=telegram" />
    </a>
    <a href="#">
        <img src="https://img.shields.io/badge/twitter-commiunity-blue?style=flat-square&logo=twitter" />
    </a>
    <a href="#">
        <img src="https://img.shields.io/github/stars/gozargah/marzban?style=social" />
    </a>
</p>

<p align="center">
 <a href="./README.md">
 English
 </a>
 /
 <a href="./README-fa.md">
 فارسی
 </a>
  /
  <a href="./README-zh-cn.md">
 简体中文
 </a>
   /
  <a href="./README-ru.md">
 Русский
 </a>
</p>

> **Mr.shaw community fork:** This repository preserves the upstream Marzban project and adds per-node health, one residential outbound per Node, and a user-level device-registration limit. Read [Fork features](FORK_FEATURES.md), the [Changelog](CHANGELOG.md), and the [API and release guide](MR_SHAW_API_AND_RELEASE.md) to see what is implemented, how its interfaces work, and what remains in development. The current image is published, but server acceptance is still pending.

The 2026-10-02 paired Node online-user statistics, policy acknowledgement/status, and device credentials are documented in [Node activity and policy contracts](docs/NODE_ACTIVITY_AND_POLICY.md). The 2026-10-03 compatibility fix is published in `latest` and awaits server acceptance: clients without `X-HWID` receive their original shared subscription, and the panel retains that shared account on the main core and Nodes. HWID-aware requests still register/reuse private credentials and reject excess new HWIDs with HTTP 429. **The shared compatibility path can bypass HWID limits; this is not a universal physical-device or online-device limit.** Node policy acknowledgements do not prove all clients are blocked. Node/scripts runtime, UI, database schema, certificates, ports and fixed Xray `v26.3.27` are unchanged; this panel-only fix does not require a Node update. Server acceptance must be repeated after publication.

For every code, API, configuration, UI, Xray-core, or documentation change, follow this repository's [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) and [`docs/REPOSITORY_UPDATE_FLOW.md`](docs/REPOSITORY_UPDATE_FLOW.md). A change is not considered released until the matching Node and scripts records, API/configuration notes, tests, GitHub Actions result, image digest, and server acceptance status are recorded. If this repository changes only the UI, the release record must explicitly say that API, database, Node channel, certificates, and ports are unchanged.

<p align="center">
  <a href="https://github.com/gozargah/marzban" target="_blank" rel="noopener noreferrer" >
    <img src="https://github.com/Gozargah/Marzban-docs/raw/master/screenshots/preview.png" alt="Marzban screenshots" width="600" height="auto">
  </a>
</p>

## Table of Contents

- [Overview](#overview)
  - [Why using Marzban?](#why-using-marzban)
    - [Features](#features)
- [Installation guide](#installation-guide)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [API](#api)
- [Backup](#backup)
- [Telegram Bot](#telegram-bot)
- [Marzban CLI](#marzban-cli)
- [Marzban Node](#marzban-node)
- [Webhook notifications](#webhook-notifications)
- [Donation](#donation)
- [License](#license)
- [Contributors](#contributors)

# Overview

Marzban (the Persian word for "border guard" - pronounced /mærz'ban/) is a proxy management tool that provides a simple and easy-to-use user interface for managing hundreds of proxy accounts powered by [Xray-core](https://github.com/XTLS/Xray-core) and built using Python and Reactjs.

## Why using Marzban?

Marzban is user-friendly, feature-rich and reliable. It lets you to create different proxies for your users without any complicated configuration. Using its built-in web UI, you are able to monitor, modify and limit users.

### Features

- Built-in **Web UI**
- Fully **REST API** backend
- [**Multiple Nodes**](#marzban-node) support (for infrastructure distribution & scalability)
- Supports protocols **Vmess**, **VLESS**, **Trojan** and **Shadowsocks**
- **Multi-protocol** for a single user
- **Multi-user** on a single inbound
- **Multi-inbound** on a **single port** (fallbacks support)
- **Traffic** and **expiry date** limitations
- **Periodic** traffic limit (e.g. daily, weekly, etc.)
- **Subscription link** compatible with **V2ray** _(such as V2RayNG, SingBox, Nekoray, etc.)_, **Clash** and **ClashMeta**
- Automated **Share link** and **QRcode** generator
- System monitoring and **traffic statistics**
- Customizable xray configuration
- **TLS** and **REALITY** support
- Integrated **Telegram Bot**
- Integrated **Command Line Interface (CLI)**
- **Multi-language**
- **Multi-admin** support (WIP)

# Installation guide

Run the following command to install Marzban with SQLite database:

```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban.sh)" @ install
```

Run the following command to install Marzban with MySQL database:

```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban.sh)" @ install --database mysql
```

Run the following command to install Marzban with MariaDB database:
```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban.sh)" @ install --database mariadb
```

Once the installation is complete:

- You will see the logs that you can stop watching them by closing the terminal or pressing `Ctrl+C`
- The Marzban files will be located at `/opt/marzban`
- The configuration file can be found at `/opt/marzban/.env` (refer to [configurations](#configuration) section to see variables)
- The data files will be placed at `/var/lib/marzban`
- For security reasons, the Marzban dashboard is not accessible via IP address. Therefore, you must [obtain SSL certificate](https://gozargah.github.io/marzban/en/examples/issue-ssl-certificate) and access your Marzban dashboard by opening a web browser and navigating to `https://YOUR_DOMAIN:8000/dashboard/` (replace YOUR_DOMAIN with your actual domain)
- You can also use SSH port forwarding to access the Marzban dashboard locally without a domain. Replace `user@serverip` with your actual SSH username and server IP and Run the command below:

```bash
ssh -L 8000:localhost:8000 user@serverip
```

Finally, you can enter the following link in your browser to access your Marzban dashboard:

http://localhost:8000/dashboard/

You will lose access to the dashboard as soon as you close the SSH terminal. Therefore, this method is recommended only for testing purposes.

Next, you need to create a sudo admin for logging into the Marzban dashboard by the following command

```bash
marzban cli admin create --sudo
```

That's it! You can login to your dashboard using these credentials

To see the help message of the Marzban script, run the following command

```bash
marzban --help
```

If you are eager to run the project using the source code, check the section below
<details markdown="1">
<summary><h3>Manual install (advanced)</h3></summary>

Install xray on your machine

You can install it using [Xray-install](https://github.com/XTLS/Xray-install)

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

Clone this project and install the dependencies (you need Python >= 3.8)

```bash
git clone https://github.com/kissow/Marzban.git
cd Marzban
wget -qO- https://bootstrap.pypa.io/get-pip.py | python3 -
python3 -m pip install -r requirements.txt
```

Alternatively, to have an isolated environment you can use [Python Virtualenv](https://pypi.org/project/virtualenv/)

Then run the following command to run the database migration scripts

```bash
alembic upgrade head
```

If you want to use `marzban-cli`, you should link it to a file in your `$PATH`, make it executable, and install the auto-completion:

```bash
sudo ln -s $(pwd)/marzban-cli.py /usr/bin/marzban-cli
sudo chmod +x /usr/bin/marzban-cli
marzban-cli completion install
```

Now it's time to configuration

Make a copy of `.env.example` file, take a look and edit it using a text editor like `nano`.

You probably like to modify the admin credentials.

```bash
cp .env.example .env
nano .env
```

> Check [configurations](#configuration) section for more information

Eventually, launch the application using command below

```bash
python3 main.py
```

To launch with linux systemctl (copy marzban.service file to `/var/lib/marzban/marzban.service`)

```
systemctl enable /var/lib/marzban/marzban.service
systemctl start marzban
```

To use with nginx

```
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name  example.com;

    ssl_certificate      /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key  /etc/letsencrypt/live/example.com/privkey.pem;

    location ~* /(dashboard|statics|sub|api|docs|redoc|openapi.json) {
        proxy_pass http://0.0.0.0:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # xray-core ws-path: /
    # client ws-path: /marzban/me/2087
    #
    # All traffic is proxed through port 443, and send to the xray port(2087, 2088 etc.).
    # The '/marzban' in location regex path can changed any characters by yourself.
    #
    # /${path}/${username}/${xray-port}
    location ~* /marzban/.+/(.+)$ {
        proxy_redirect off;
        proxy_pass http://127.0.0.1:$1/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

or

```
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name  marzban.example.com;

    ssl_certificate      /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key  /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://0.0.0.0:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

By default the app will be run on `http://localhost:8000/dashboard`. You can configure it using changing the `UVICORN_HOST` and `UVICORN_PORT` environment variables.
</details>

# Configuration

> You can set settings below using environment variables or placing them in `.env` file.

| Variable                                 | Description                                                                                                              |
| ---------------------------------------- |--------------------------------------------------------------------------------------------------------------------------|
| SUDO_USERNAME                            | Superuser's username                                                                                                     |
| SUDO_PASSWORD                            | Superuser's password                                                                                                     |
| SQLALCHEMY_DATABASE_URL                  | Database URL ([SQLAlchemy's docs](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls))                    |
| UVICORN_HOST                             | Bind application to this host (default: `0.0.0.0`)                                                                       |
| UVICORN_PORT                             | Bind application to this port (default: `8000`)                                                                          |
| UVICORN_UDS                              | Bind application to a UNIX domain socket                                                                                 |
| UVICORN_SSL_CERTFILE                     | SSL certificate file to have application on https                                                                        |
| UVICORN_SSL_KEYFILE                      | SSL key file to have application on https                                                                                |
| UVICORN_SSL_CA_TYPE                      | Type of authority SSL certificate. Use `private` for testing self-signed CA (default: `public`)                          |
| XRAY_JSON                                | Path of Xray's json config file (default: `xray_config.json`)                                                            |
| XRAY_EXECUTABLE_PATH                     | Path of Xray binary (default: `/usr/local/bin/xray`)                                                                     |
| XRAY_ASSETS_PATH                         | Path of Xray assets (default: `/usr/local/share/xray`)                                                                   |
| XRAY_SUBSCRIPTION_URL_PREFIX             | Prefix of subscription URLs                                                                                              |
| XRAY_FALLBACKS_INBOUND_TAG               | Tag of the inbound that includes fallbacks, needed in the case you're using fallbacks                                    |
| XRAY_EXCLUDE_INBOUND_TAGS                | Tags of the inbounds that shouldn't be managed and included in links by application                                      |
| CUSTOM_TEMPLATES_DIRECTORY               | Customized templates directory (default: `app/templates`)                                                                |
| CLASH_SUBSCRIPTION_TEMPLATE              | The template that will be used for generating clash configs (default: `clash/default.yml`)                               |
| SUBSCRIPTION_PAGE_TEMPLATE               | The template used for generating subscription info page (default: `subscription/index.html`)                             |
| HOME_PAGE_TEMPLATE                       | Decoy page template (default: `home/index.html`)                                                                         |
| TELEGRAM_API_TOKEN                       | Telegram bot API token  (get token from [@botfather](https://t.me/botfather))                                            |
| TELEGRAM_ADMIN_ID                        | Numeric Telegram ID of admin (use [@userinfobot](https://t.me/userinfobot) to found your ID)                             |
| TELEGRAM_PROXY_URL                       | Run Telegram Bot over proxy                                                                                              |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES          | Expire time for the Access Tokens in minutes, `0` considered as infinite (default: `1440`)                               |
| DOCS                                     | Whether API documents should be available on `/docs` and `/redoc` or not (default: `False`)                              |
| DEBUG                                    | Debug mode for development (default: `False`)                                                                            |
| WEBHOOK_ADDRESS                          | Webhook address to send notifications to. Webhook notifications will be sent if this value was set.                      |
| WEBHOOK_SECRET                           | Webhook secret will be sent with each request as `x-webhook-secret` in the header (default: `None`)                      |
| NUMBER_OF_RECURRENT_NOTIFICATIONS        | How many times to retry if an error detected in sending a notification (default: `3`)                                    |
| RECURRENT_NOTIFICATIONS_TIMEOUT          | Timeout between each retry if an error detected in sending a notification in seconds (default: `180`)                    |
| NOTIFY_REACHED_USAGE_PERCENT             | At which percentage of usage to send the warning notification (default: `80`)                                            |
| NOTIFY_DAYS_LEFT                         | When to send warning notifaction about expiration (default: `3`)                                                         |
| USERS_AUTODELETE_DAYS                    | Delete expired (and optionally limited users) after this many days (Negative values disable this feature, default: `-1`) |
| USER_AUTODELETE_INCLUDE_LIMITED_ACCOUNTS | Whether to include limited accounts in the auto-delete feature (default: `False`)                                        |
| USE_CUSTOM_JSON_DEFAULT                  | Enable custom JSON config for ALL supported clients (default: `False`)                                                   |
| USE_CUSTOM_JSON_FOR_V2RAYNG              | Enable custom JSON config only for V2rayNG (default: `False`)                                                            |
| USE_CUSTOM_JSON_FOR_STREISAND            | Enable custom JSON config only for Streisand (default: `False`)                                                          |
| USE_CUSTOM_JSON_FOR_V2RAYN               | Enable custom JSON config only for V2rayN (default: `False`)                                                             |


# Documentation

The [Marzban Documentation](https://gozargah.github.io/marzban) provides all the essential guides to get you started, available in three languages: Farsi, English, and Russian. This documentation requires significant effort to cover all aspects of the project comprehensively. We welcome and appreciate your contributions to help us improve it. You can contribute on this [GitHub repository](https://github.com/Gozargah/gozargah.github.io).


# API

Marzban provides a REST API that enables developers to interact with Marzban services programmatically. To view the API documentation in Swagger UI or ReDoc, set the configuration variable `DOCS=True` and navigate to the `/docs` and `/redoc`.


# Backup

It's always a good idea to backup your Marzban files regularly to prevent data loss in case of system failures or accidental deletion. Here are the steps to backup Marzban:

1. By default, all Marzban important files are saved in `/var/lib/marzban` (Docker versions). Copy the entire `/var/lib/marzban` directory to a backup location of your choice, such as an external hard drive or cloud storage.
2. Additionally, make sure to backup your env file, which contains your configuration variables, and also, your Xray config file. If you installed Marzban using marzban-scripts (recommended installation approach), the env and other configurations should be inside `/opt/marzban/` directory.

Marzban's backup service efficiently zips all necessary files and sends them to your specified Telegram bot. It supports SQLite, MySQL, and MariaDB databases. One of its key features is automation, allowing you to schedule backups every hour. There are no limitations concerning Telegram's upload limits for bots; if a file exceeds the limit, it will be split and sent in multiple parts. Additionally, you can initiate an immediate backup at any time.

Install the Latest Version of Marzban Command:
```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban.sh)" @ install-script
```

Setup the Backup Service:
```bash
marzban backup-service
```

Get an Immediate Backup:
```bash
marzban backup
```

By following these steps, you can ensure that you have a backup of all your Marzban files and data, as well as your configuration variables and Xray configuration, in case you need to restore them in the future. Remember to update your backups regularly to keep them up-to-date.

# Telegram Bot

Marzban comes with an integrated Telegram bot that can handle server management, user creation and removal, and send notifications. This bot can be easily enabled by following a few simple steps, and it provides a convenient way to interact with Marzban without having to log in to the server every time.

To enable Telegram Bot:

1. set `TELEGRAM_API_TOKEN` to your bot's API Token
2. set `TELEGRAM_ADMIN_ID` to your Telegram account's numeric ID, you can get your ID from [@userinfobot](https://t.me/userinfobot)

# Marzban CLI

Marzban comes with an integrated CLI named `marzban-cli` which allows administrators to have direct interaction with it.

If you've installed Marzban using easy install script, you can access the cli commands by running

```bash
marzban cli [OPTIONS] COMMAND [ARGS]...
```

For more information, You can read [Marzban CLI's documentation](./cli/README.md).

# Marzban Node

The Marzban project introduces the [Marzban-node](https://github.com/gozargah/marzban-node), which revolutionizes infrastructure distribution. With Marzban-node, you can distribute your infrastructure across multiple locations, unlocking benefits such as redundancy, high availability, scalability, flexibility. Marzban-node empowers users to connect to different servers, offering them the flexibility to choose and connect to multiple servers instead of being limited to only one server.
For more detailed information and installation instructions, please refer to the [Marzban-node official documentation](https://github.com/gozargah/marzban-node)

# Webhook notifications

You can set a webhook address and Marzban will send the notifications to that address.

the requests will be sent as a post request to the adress provided by `WEBHOOK_ADDRESS` with `WEBHOOK_SECRET` as `x-webhook-secret` in the headers.

Example request sent from Marzban:

```
Headers:
Host: 0.0.0.0:9000
User-Agent: python-requests/2.28.1
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
x-webhook-secret: something-very-very-secret
Content-Length: 107
Content-Type: application/json



Body:
{"username": "marzban_test_user", "action": "user_updated", "enqueued_at": 1680506457.636369, "tries": 0}
```

Different action typs are: `user_created`, `user_updated`, `user_deleted`, `user_limited`, `user_expired`, `user_disabled`, `user_enabled`

# Donation

The addresses below support development and maintenance of the **Mr.shaw community fork**. This fork is based on [Gozargah/Marzban](https://github.com/Gozargah/Marzban); thank you to the upstream authors and contributors. To support the original project instead, use its [upstream donation section](https://github.com/Gozargah/Marzban#donation).

- USDT•TRON (TRC20): `TXWN1uwo9X6mXizcb4hJPTquEmvWWgMftU`
- USDT•BNB Smart Chain (BEP20): `0xeC3f0fb7B6F4003A903bB3d75853115dCA6BF078`

Thank you for your support!

# License

Made in [Unknown!] and Published under [AGPL-3.0](./LICENSE).

# Contributors

We ❤️‍🔥 contributors! If you'd like to contribute, please check out our [Contributing Guidelines](CONTRIBUTING.md) and feel free to submit a pull request or open an issue. We also welcome you to join our [Telegram](https://t.me/gozargah_marzban) group for either support or contributing guidance.

Check [open issues](https://github.com/gozargah/marzban/issues) to help the progress of this project.

<p align="center">
Thanks to the all contributors who have helped improve Marzban:
</p>
<p align="center">
<a href="https://github.com/Gozargah/Marzban/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Gozargah/Marzban" />
</a>
</p>
<p align="center">
  Made with <a rel="noopener noreferrer" target="_blank" href="https://contrib.rocks">contrib.rocks</a>
</p>
