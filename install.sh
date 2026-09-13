#!/usr/bin/env bash
# =============================================================================
#  FnOS Mihomo & Clash Node Hub 一键部署与启动脚本
# =============================================================================
set -e

INSTALL_DIR="/vol1/1000/Docker/fnos-node-hub"
SERVICE_NAME="fnos-node-hub.service"
PORT=7788

echo "============================================================"
echo "  🚀 正在安装/更新 FnOS 代理节点管理面板 (Mihomo/Clash)"
echo "============================================================"

# 1. 检查 Python 环境
if ! command -v python3 &>/dev/null; then
    echo "❌ 未检测到 Python3，请先安装 python3 (sudo apt update && sudo apt install -y python3 python3-pip)"
    exit 1
fi

# 2. 安装 Python 依赖
echo "📦 安装依赖中..."
pip3 install --break-system-packages fastapi uvicorn pyyaml requests paramiko || pip3 install fastapi uvicorn pyyaml requests paramiko

# 3. 创建目录与复制文件 (若当前就在源码目录下)
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$CURRENT_DIR" != "$INSTALL_DIR" ]; then
    echo "📂 同步文件到 $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"
fi

chmod -R 755 "$INSTALL_DIR"

# 4. 配置 Systemd 开机自启服务
echo "⚙️ 配置 Systemd 服务..."
cat <<EOF > /etc/systemd/system/${SERVICE_NAME}
[Unit]
Description=FnOS Mihomo and Clash Node Hub (Web UI)
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/server.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 5. 重载并启动服务
systemctl daemon-reload
systemctl enable --now ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo ""
echo "============================================================"
echo "  🎉 部署完成！"
echo "  👉 访问地址: http://<飞牛NAS_IP>:${PORT}"
echo "  👉 状态检查: sudo systemctl status ${SERVICE_NAME}"
echo "============================================================"
