# 🚀 FnOS 飞牛代理节点管理面板 (Mihomo & Clash Node Hub)

<div align="center">

![FnOS Node Hub](https://img.shields.io/badge/FnOS-Supported-blue?style=flat-square&logo=linux)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)
![Vue 3](https://img.shields.io/badge/Vue.js-3.x-4FC08D?style=flat-square&logo=vuedotjs)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.x-38B2AC?style=flat-square&logo=tailwind-css)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**专为飞牛 NAS (fnOS) 打造的轻量级现代化 Web 代理节点与策略管理面板**

*让在飞牛上运行的 Mihomo / Clash 拥有直观的可视化节点维护能力*

[功能特性](#-功能特性) • [一键部署](#-飞牛-fnos-部署教程) • [使用指南](#-功能使用指南) • [常见问题](#-常见问题与排错)

</div>

---

## 📖 项目背景

在飞牛 NAS (fnOS) 上通过 Docker 搭建 Mihomo (Clash.Meta) 或 Clash 之后，官方或常规面板（如 Metacubexd、Yacd）主要用于查看实时流量和切换当前生效节点，**无法直接对节点进行增删改查、导入新节点或修改配置参数**。

本项目填补了这一空白，提供了一个专用的 Web 管理面板，直接与飞牛上的 Mihomo / Clash 配置文件对接，让你可以像在桌面客户端一样轻松管理 NAS 上的代理节点与分流规则。

---

## 🌟 功能特性

- 🛰️ **全协议节点可视化管理**：
  - 原生支持 **VLESS** (含 Reality / TLS / Vision 流控)、**VMess**、**Trojan**、**Shadowsocks**、**Hysteria2** 等全部主流协议。
  - 节点列表卡片/表格切换，直观展示 IP、端口、传输模式、加密安全与证书状态。
  - 支持节点复制克隆、编辑修改、一键复制导出分享链接（`vless://`、`vmess://`、`trojan://` 等）。
- ⚡ **多途径极速导入**：
  - **快捷解析**：添加节点时直接粘贴单条链接，自动解析提取所有字段。
  - **批量导入**：支持同时粘贴多条节点链接、Base64 订阅文本或 Clash 节点 YAML 块。
  - **订阅 URL 在线拉取**：输入机场订阅链接，在线拉取节点列表，支持多选勾选后批量加入。
- ⏱️ **节点延迟测试**：
  - 支持单节点延迟测试与全节点一键并发测速，延迟状态高亮显示（绿色优质 / 黄色一般 / 红色超时）。
- 🧭 **策略组 (Proxy Groups) 可视化分配**：
  - 直观调整各个节点在 `PROXY`、`TMDB`、`DIRECT` 等策略组中的分配。
  - 支持一键新增自定义策略组。
- 🛡️ **分流规则 (Routing Rules) 管理**：
  - 查看与添加分流规则（`DOMAIN-SUFFIX`、`IP-CIDR`、`GEOIP`、`MATCH` 等），支持上下调整优先级。
- 🔄 **无缝热重载与核心管理**：
  - 保存修改时自动调用 Mihomo 核心 Controller API 进行热加载生效，无需断网重启；
  - 提供一键重启 Mihomo 容器快捷操作。
- 🛡️ **安全自动备份与一键回滚**：
  - 每次保存均自动在飞牛上生成带时间戳的备份文件（如 `config.yaml.bak_YYYYMMDD_HHMMSS`）；
  - 界面内提供历史备份列表，随时一键还原历史版本。
- 📝 **内置 YAML 源码编辑器**：
  - 支持直接在线查看与编辑完整 `config.yaml` 源码，带语法校验。

---

## 📦 飞牛 (fnOS) 部署教程

### 方式一：一键自动安装（推荐，最省心）

通过 SSH 连接到飞牛 NAS（可以使用 Putty、Terminal 或飞牛自带终端）：

```bash
# 1. 下载项目代码
git clone https://github.com/2290145679/fnos-node-hub.git /vol1/1000/Docker/fnos-node-hub

# 2. 进入项目目录并执行安装脚本
cd /vol1/1000/Docker/fnos-node-hub
sudo bash install.sh
```

> 安装完成后，直接在浏览器中打开：`http://<飞牛IP>:7788` 即可使用！

---

### 方式二：手动 Systemd 服务安装

如果你希望手动控制每一步：

#### 1. 安装 Python 依赖
```bash
sudo apt update
sudo apt install -y python3 python3-pip
sudo pip3 install --break-system-packages fastapi uvicorn pyyaml requests paramiko
```

#### 2. 下载并放置项目文件
```bash
sudo mkdir -p /vol1/1000/Docker/fnos-node-hub
sudo git clone https://github.com/2290145679/fnos-node-hub.git /vol1/1000/Docker/fnos-node-hub
sudo chown -R root:root /vol1/1000/Docker/fnos-node-hub
```

#### 3. 配置开机自启系统服务
创建服务文件 `/etc/systemd/system/fnos-node-hub.service`：
```ini
[Unit]
Description=FnOS Mihomo and Clash Node Hub (Web UI)
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/vol1/1000/Docker/fnos-node-hub
ExecStart=/usr/bin/python3 /vol1/1000/Docker/fnos-node-hub/server.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

#### 4. 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fnos-node-hub.service
```

---

### 方式三：使用 Docker Compose 部署

如果你偏好完全容器化运行：

```bash
cd /vol1/1000/Docker/fnos-node-hub
sudo docker compose up -d
```

---

## 🖥️ 本地电脑独立运行模式（Windows / Mac）

如果你不想在飞牛上常驻 Python 服务，也可以把本工具放在个人电脑上运行，通过 SSH 远程连接管理飞牛：

1. 双击运行 `start.bat`（Windows）或在终端执行 `python server.py`；
2. 浏览器自动打开 `http://127.0.0.1:8899`；
3. 点击面板右上角的 **设置**，填入你的飞牛 SSH 账户与密码即可远程管理。

---

## ⚙️ 默认路径与端口说明

| 项目 | 默认值 | 说明 |
| :--- | :--- | :--- |
| **Web 访问端口** | `7788` | 浏览器访问 `http://<飞牛IP>:7788` |
| **Mihomo 配置文件** | `/vol1/1000/Docker/mihomo/config/config.yaml` | 飞牛上的 Mihomo 核心配置 |
| **Clash 配置文件** | `/vol1/1000/Docker/clash/clash.yml` | 飞牛上的 Clash 核心配置 |
| **Mihomo 核心 API** | `http://127.0.0.1:9092` | 用于触发热重载和节点测速 |
| **Mihomo 密钥 (Secret)** | `Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n` | Mihomo 外部控制密钥 |

> 💡 *注：以上配置均可在 Web 面板右上角“设置”或 `server.py` 中自定义修改。*

---

## 🛠️ 服务常用命令 (飞牛终端)

```bash
# 查看面板运行状态
sudo systemctl status fnos-node-hub.service

# 重启面板服务
sudo systemctl restart fnos-node-hub.service

# 停止面板服务
sudo systemctl stop fnos-node-hub.service

# 查看面板运行日志
sudo journalctl -u fnos-node-hub.service -f
```

---

## ❓ 常见问题与排错

### 1. 修改节点后点击“保存并生效”没有起效？
- 面板保存时会自动通过 `9092` 端口通知 Mihomo 重新加载配置。如果热重载未生效，可以点击右上角“**重启容器**”按钮强制重启 Mihomo 容器。

### 2. 测速全部显示超时？
- 请确保 Mihomo 容器正在运行，且 `9092` 端口正常监听。
- 可以在飞牛上执行 `docker ps` 查看 Mihomo 容器状态。

### 3. 如何回滚到之前的配置？
- 点击页面顶部的 **“YAML 源码 & 备份”** 标签页，右侧会列出历次保存时自动生成的备份文件，点击对应条目后的 **“恢复此版本”** 即可一键恢复。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
