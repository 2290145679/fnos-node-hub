#!/usr/bin/env bash
# =============================================================================
#  FnOS 飞牛代理节点管理面板 (Mihomo & Clash Node Hub) 一键交互式安装管理脚本
# =============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

INSTALL_DIR="/vol1/1000/Docker/fnos-node-hub"
SERVICE_NAME="fnos-node-hub.service"
GITHUB_REPO="https://github.com/2290145679/fnos-node-hub.git"
GITHUB_RAW="https://raw.githubusercontent.com/2290145679/fnos-node-hub/main"

# 确保以 root / sudo 权限运行
if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}❌ 错误: 请使用 root 或 sudo 权限运行此脚本！${NC}"
    echo -e "例如: ${CYAN}sudo bash <(curl -sSL https://raw.githubusercontent.com/2290145679/fnos-node-hub/main/install.sh)${NC}"
    exit 1
fi

# 获取本机局域网 IP
get_local_ip() {
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$ip" ]; then
        ip=$(ip route get 1.1.1.1 2>/dev/null | awk -F"src " 'NR==1{split($2,a," ");print a[1]}')
    fi
    if [ -z "$ip" ]; then
        ip="192.168.1.57"
    fi
    echo "$ip"
}

# 打印横幅
print_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "================================================================="
    echo "       🚀 FnOS 飞牛代理节点管理面板 (Mihomo & Clash)             "
    echo "              一键交互式安装 / 管理维护脚本                     "
    echo "================================================================="
    echo -e "${NC}"
}

# 交互式读取函数 (兼容 curl | bash 管道模式)
prompt_input() {
    local prompt="$1"
    local default_val="$2"
    local var_name="$3"
    local user_val=""

    if [ -t 0 ]; then
        read -r -p "$(echo -e "$prompt")" user_val
    else
        read -r -p "$(echo -e "$prompt")" user_val </dev/tty
    fi

    if [ -z "$user_val" ]; then
        user_val="$default_val"
    fi
    eval "$var_name=\"$user_val\""
}

# 检查并安装环境依赖
install_dependencies() {
    echo -e "\n${BLUE}🔍 [1/4] 检查系统环境与 Python 依赖...${NC}"
    
    # 检查 Python3
    if ! command -v python3 &>/dev/null; then
        echo -e "${YELLOW}⚡ 正在安装 Python3 及必要组件...${NC}"
        apt-get update -y && apt-get install -y python3 python3-pip git curl
    fi

    # 检查 pip3
    if ! command -v pip3 &>/dev/null; then
        apt-get install -y python3-pip
    fi

    # 安装 Python 库
    echo -e "${YELLOW}📦 正在安装后端依赖库 (FastAPI, Uvicorn, PyYAML, Requests)...${NC}"
    pip3 install --break-system-packages fastapi uvicorn pyyaml requests paramiko || pip3 install fastapi uvicorn pyyaml requests paramiko
    echo -e "${GREEN}✅ 环境依赖检查完成！${NC}"
}

# 安装或更新面板
do_install() {
    print_banner
    echo -e "${BOLD}即将开始配置并安装 FnOS 代理节点管理面板${NC}\n"
    echo -e "👉 ${YELLOW}按回车键将使用方括号 [ ] 中的默认推荐值${NC}\n"

    # 1. 端口配置
    prompt_input "${CYAN}▶ 请输入 Web 面板访问端口 [默认: ${BOLD}7788${NC}${CYAN}]: ${NC}" "7788" PORT

    # 2. 查找默认 Mihomo 路径
    DEFAULT_MIHOMO_PATH="/vol1/1000/Docker/mihomo/config/config.yaml"
    if [ ! -f "$DEFAULT_MIHOMO_PATH" ]; then
        FOUND_PATH=$(find /vol1 /volume1 /home -name "config.yaml" 2>/dev/null | grep -E "mihomo|clash" | head -n 1)
        if [ -n "$FOUND_PATH" ]; then
            DEFAULT_MIHOMO_PATH="$FOUND_PATH"
        fi
    fi
    prompt_input "${CYAN}▶ 请输入 Mihomo 配置文件绝对路径 [默认: ${BOLD}${DEFAULT_MIHOMO_PATH}${NC}${CYAN}]: ${NC}" "$DEFAULT_MIHOMO_PATH" MIHOMO_PATH

    # 3. 核心 API 地址与密钥
    prompt_input "${CYAN}▶ 请输入 Mihomo 核心 Controller API [默认: ${BOLD}http://127.0.0.1:9092${NC}${CYAN}]: ${NC}" "http://127.0.0.1:9092" MIHOMO_API
    prompt_input "${CYAN}▶ 请输入 Mihomo 外部控制密钥 (Secret) [默认: ${BOLD}Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n${NC}${CYAN}]: ${NC}" "Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n" MIHOMO_SECRET

    echo -e "\n${PURPLE}-----------------------------------------------------------------${NC}"
    echo -e "  ⚙️ 配置确认："
    echo -e "  - Web 端口:          ${BOLD}${PORT}${NC}"
    echo -e "  - 配置文件路径:      ${BOLD}${MIHOMO_PATH}${NC}"
    echo -e "  - Mihomo 核心 API:   ${BOLD}${MIHOMO_API}${NC}"
    echo -e "  - Mihomo 密钥:       ${BOLD}${MIHOMO_SECRET}${NC}"
    echo -e "${PURPLE}-----------------------------------------------------------------${NC}\n"

    # 执行安装
    install_dependencies

    echo -e "\n${BLUE}📂 [2/4] 准备项目目录并拉取最新文件...${NC}"
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}/static"

    # 如果已经在仓库目录中运行，则直接复制；否则从 GitHub 拉取
    CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$CURRENT_DIR/server.py" ] && [ -d "$CURRENT_DIR/static" ]; then
        echo -e "${YELLOW}📋 检测到本地安装包，正在复制文件...${NC}"
        cp -r "$CURRENT_DIR"/* "${INSTALL_DIR}/" 2>/dev/null || true
    else
        echo -e "${YELLOW}🌐 正在从 GitHub 克隆/更新最新代码...${NC}"
        if [ -d "${INSTALL_DIR}/.git" ]; then
            cd "${INSTALL_DIR}" && git pull origin main
        else
            rm -rf "${INSTALL_DIR}"
            git clone "${GITHUB_REPO}" "${INSTALL_DIR}"
        fi
    fi

    # 替换 server.py 中的自定义配置
    echo -e "\n${BLUE}⚙️ [3/4] 写入自定义参数到配置文件...${NC}"
    python3 -c "
import re

server_file = '${INSTALL_DIR}/server.py'
with open(server_file, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace settings
code = re.sub(r'\"remote_path\":\s*\"[^\"]*\"', '\"remote_path\": \"${MIHOMO_PATH}\"', code)
code = re.sub(r'\"mihomo_api\":\s*\"[^\"]*\"', '\"mihomo_api\": \"${MIHOMO_API}\"', code)
code = re.sub(r'\"mihomo_secret\":\s*\"[^\"]*\"', '\"mihomo_secret\": \"${MIHOMO_SECRET}\"', code)
code = re.sub(r'\"port\":\s*\d+', '\"port\": ${PORT}', code)
code = re.sub(r'port=\d+', 'port=${PORT}', code)

with open(server_file, 'w', encoding='utf-8') as f:
    f.write(code)
"

    # 设置权限
    chmod -R 755 "${INSTALL_DIR}"

    # 配置 Systemd 服务
    echo -e "\n${BLUE}🚀 [4/4] 创建并注册 Systemd 开机自启服务...${NC}"
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

    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}
    systemctl restart ${SERVICE_NAME}

    sleep 2

    # 验证服务状态
    LOCAL_IP=$(get_local_ip)
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "\n${GREEN}${BOLD}=================================================================${NC}"
        echo -e "${GREEN}${BOLD}  🎉 恭喜！FnOS 代理节点管理面板已成功部署并启动！${NC}"
        echo -e "${GREEN}${BOLD}=================================================================${NC}"
        echo -e "\n👉 ${BOLD}浏览器访问地址:${NC} ${CYAN}http://${LOCAL_IP}:${PORT}${NC}"
        echo -e "👉 ${BOLD}服务运行状态:${NC}   ${GREEN}active (running)${NC} (已设为开机自启)"
        echo -e "👉 ${BOLD}安装路径:${NC}       ${INSTALL_DIR}\n"
    else
        echo -e "\n${RED}⚠️ 服务启动异常，请使用 'sudo systemctl status ${SERVICE_NAME}' 查看日志排查原因。${NC}"
    fi
}

# 服务管理子菜单
manage_service() {
    local action="$1"
    case "$action" in
        status)
            systemctl status ${SERVICE_NAME} --no-pager
            ;;
        restart)
            systemctl restart ${SERVICE_NAME}
            echo -e "${GREEN}✅ 服务已重启！${NC}"
            ;;
        stop)
            systemctl stop ${SERVICE_NAME}
            echo -e "${YELLOW}🛑 服务已停止！${NC}"
            ;;
        start)
            systemctl start ${SERVICE_NAME}
            echo -e "${GREEN}▶️ 服务已启动！${NC}"
            ;;
        log)
            echo -e "${CYAN}正在查看实时运行日志 (按 Ctrl+C 退出):${NC}"
            journalctl -u ${SERVICE_NAME} -f
            ;;
    esac
}

# 卸载面板
do_uninstall() {
    echo -e "${RED}${BOLD}⚠️ 确定要卸载 FnOS 代理节点管理面板吗？${NC}"
    prompt_input "确认卸载请输入 y，取消请输入 n [y/n]: " "n" CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        echo -e "${YELLOW}正在停止并移除系统服务...${NC}"
        systemctl stop ${SERVICE_NAME} 2>/dev/null || true
        systemctl disable ${SERVICE_NAME} 2>/dev/null || true
        rm -f /etc/systemd/system/${SERVICE_NAME}
        systemctl daemon-reload

        prompt_input "是否同时删除项目代码目录 (${INSTALL_DIR})？[y/n]: " "y" DEL_DIR
        if [ "$DEL_DIR" = "y" ] || [ "$DEL_DIR" = "Y" ]; then
            rm -rf "${INSTALL_DIR}"
            echo -e "${GREEN}✅ 项目文件已清理！${NC}"
        fi
        echo -e "${GREEN}🎉 卸载完成！${NC}"
    else
        echo -e "${BLUE}已取消卸载。${NC}"
    fi
}

# 主菜单
main_menu() {
    while true; do
        print_banner
        # 检测当前状态
        if systemctl is-active --quiet ${SERVICE_NAME} 2>/dev/null; then
            echo -e "当前运行状态: ${GREEN}${BOLD}● 正在运行 (端口: $(ss -tulpn | grep -E '7788|server.py' | awk '{print $5}' | head -n 1 | awk -F: '{print $NF}' || echo '7788'))${NC}"
        else
            echo -e "当前运行状态: ${RED}${BOLD}○ 未运行 / 未安装${NC}"
        fi
        echo ""
        echo -e "  ${GREEN}1.${NC} 安装 / 重新配置 / 更新面板"
        echo -e "  ${GREEN}2.${NC} 启动服务"
        echo -e "  ${GREEN}3.${NC} 重启服务"
        echo -e "  ${GREEN}4.${NC} 停止服务"
        echo -e "  ${GREEN}5.${NC} 查看服务运行状态"
        echo -e "  ${GREEN}6.${NC} 查看实时运行日志"
        echo -e "  ${GREEN}7.${NC} 卸载面板"
        echo -e "  ${GREEN}0.${NC} 退出脚本"
        echo ""
        prompt_input "${CYAN}请输入操作序号 [0-7]: ${NC}" "1" CHOICE

        case "$CHOICE" in
            1)
                do_install
                break
                ;;
            2)
                manage_service start
                sleep 2
                ;;
            3)
                manage_service restart
                sleep 2
                ;;
            4)
                manage_service stop
                sleep 2
                ;;
            5)
                manage_service status
                echo ""
                prompt_input "按回车键返回主菜单..." "" DUMMY
                ;;
            6)
                manage_service log
                ;;
            7)
                do_uninstall
                break
                ;;
            0)
                echo -e "${BLUE}再见！${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}输入无效，请重新输入！${NC}"
                sleep 1
                ;;
        esac
    done
}

# 入口
if [ "$1" = "install" ]; then
    do_install
else
    main_menu
fi
