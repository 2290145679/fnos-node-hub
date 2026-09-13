@echo off
title FnOS Mihomo & Clash Node Hub
cd /d %~dp0
echo ====================================================
echo   FnOS 飞牛代理节点管理面板 (Mihomo / Clash)
echo ====================================================
echo 正在启动 Web 服务...
start http://127.0.0.1:8899
python server.py
pause
