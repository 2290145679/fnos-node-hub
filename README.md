# 🚀 FnOS 飞牛代理节点管理面板 (Mihomo & Clash Node Hub)

<div align="center">

![FnOS Node Hub](https://img.shields.io/badge/FnOS-Supported-blue?style=flat-square&logo=linux)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)
![Vue 3](https://img.shields.io/badge/Vue.js-3.x-4FC08D?style=flat-square&logo=vuedotjs)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.x-38B2AC?style=flat-square&logo=tailwind-css)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**专为飞牛 NAS (fnOS) 打造的现代化轻量级 Web 代理节点与策略管理面板**

*让在飞牛上运行的 Mihomo / Clash 拥有直观的可视化节点增删改查、延迟测速与无缝热重载能力*

[🔥 一键安装指令](#-飞牛-fnos-一键指令安装推荐-) • [🌟 功能特性](#-功能特性) • [🔑 参数与密钥详解](#-关键配置参数与密钥说明) • [⚙️ 管理与维护](#-服务管理与维护) • [❓ 常见问题](#-常见问题与排错)

</div>

---

## 🔥 飞牛 (fnOS) 一键指令安装（推荐 🌟）

在飞牛 NAS 的终端（SSH 或飞牛自带终端）中直接运行下面**这一行命令**：

```bash
curl -sSL https://raw.githubusercontent.com/2290145679/fnos-node-hub/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
```

> 💡 **交互式配置说明**：
> 运行命令后会自动弹出全彩交互菜单，脚本已自动检测系统环境并内置了推荐默认值，**直接一路按回车确认**即可秒级完成安装与配置！
> 
> 安装完成后，会自动配置好 **开机自启系统服务**，并在屏幕上打印出管理面板的 Web 访问地址（例如 `http://192.168.1.57:7788`）！

```
=================================================================
       🚀 FnOS 飞牛代理节点管理面板 (Mihomo & Clash)             
              一键交互式安装 / 管理维护脚本                     
=================================================================

  1. 安装 / 重新配置 / 更新面板
  2. 启动服务
  3. 重启服务
  4. 停止服务
  5. 查看服务运行状态
  6. 查看实时运行日志
  7. 卸载面板
  0. 退出脚本
```

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
  - 直观勾选调整各个节点在 `PROXY`、`TMDB`、`DIRECT` 等策略组中的分配。
  - 支持一键新增自定义策略组。
- 🛡️ **分流规则 (Routing Rules) 管理**：
  - 查看与添加分流规则（`DOMAIN-SUFFIX`、`IP-CIDR`、`GEOIP`、`MATCH` 等），支持上下调整优先级。
- 🔄 **无缝热重载与核心管理**：
  - 保存修改时自动调用 Mihomo 核心 Controller API 进行热加载生效，无需断网重启；
  - 面板提供一键重启 Mihomo 容器快捷操作。
- 🛡️ **安全自动备份与一键回滚**：
  - 每次保存均自动在飞牛上生成带时间戳的备份文件（如 `config.yaml.bak_YYYYMMDD_HHMMSS`）；
  - 界面内提供历史备份列表，随时一键还原历史版本。
- 📝 **内置 YAML 源码编辑器**：
  - 支持直接在线查看与编辑完整 `config.yaml` 源码，带语法校验。

---

## 🔑 关键配置参数与密钥说明

在安装过程中或面板设置中涉及以下 4 个核心参数，这里做出详细解读：

```
+-------------------------------------------------------------------------------+
|                             FnOS 节点管理面板 (Web)                           |
|                               (端口: 7788)                                    |
+---------------------------------------+---------------------------------------+
                                        |
       1. 读写配置文件                  | 2. API 通信 (带着 Secret 密钥)
       (/vol1/1000/Docker/mihomo/...)   | (http://127.0.0.1:9092)
                                        v
+-------------------------------------------------------------------------------+
|                       Mihomo / Clash 核心容器 (Docker)                         |
|  - 配置文件: config.yaml                                                      |
|  - Controller 端口: 9092                                                      |
|  - Secret 访问密钥: "Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n"                        |
+-------------------------------------------------------------------------------+
```

| 参数项 | 默认推荐值 | 详细说明 |
| :--- | :--- | :--- |
| **Web 访问端口** | `7788` | 您在浏览器中访问本面板的端口，例如 `http://<飞牛IP>:7788`。 |
| **Mihomo 配置文件路径** | `/vol1/1000/Docker/mihomo/config/config.yaml` | 飞牛上 Mihomo 容器挂载的实际配置文件路径，面板在此基础上修改节点并做自动备份。 |
| **Mihomo 核心 API 地址** | `http://127.0.0.1:9092` | Mihomo 核心暴露的外部控制端口（`external-controller`），用于测延迟和通知配置生效。 |
| **Mihomo 外部控制密钥 (Secret)** | `Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n` | **Mihomo API 访问密码**。写在 `config.yaml` 开头的 `secret:` 字段中。面板每次测延迟或热重载时均需提供此密码鉴权。安装时直接回车即可！ |

> 💡 *注：以上参数均可在安装时按回车保持默认，也可以在 Web 面板右上角“设置”中随时自定义。*

---

## 🛠️ 服务管理与维护

在飞牛终端随时再次运行安装命令即可进入多功能管理菜单：

```bash
curl -sSL https://raw.githubusercontent.com/2290145679/fnos-node-hub/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
```

也可以使用标准的 Linux 服务命令：

```bash
# 查看面板运行状态
sudo systemctl status fnos-node-hub.service

# 重启面板服务
sudo systemctl restart fnos-node-hub.service

# 停止面板服务
sudo systemctl stop fnos-node-hub.service

# 查看面板实时运行日志
sudo journalctl -u fnos-node-hub.service -f
```

---

## ❓ 常见问题与排错

### 1. 修改节点后点击“保存并生效”没有起效？
- 面板保存时会自动通过 `9092` 端口通知 Mihomo 重新加载配置。如果热重载未生效，可以点击右上角“**重启容器**”按钮强制重启 Mihomo 容器。

### 2. 测速全部显示超时？
- 请确保 Mihomo 容器正在运行，且 `9092` 端口正常监听。
- 检查 `config.yaml` 里的 `secret` 是否与面板设置中的密钥一致。
- 可以在飞牛上执行 `docker ps` 查看 Mihomo 容器状态。

### 3. 如何回滚到之前的配置？
- 点击页面顶部的 **“YAML 源码 & 备份”** 标签页，右侧会列出历次保存时自动生成的备份文件，点击对应条目后的 **“恢复此版本”** 即可一键恢复。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
