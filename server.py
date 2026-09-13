import os
import sys
import time
import json
import logging
import datetime
import urllib.parse
from typing import Dict, Any, List, Optional
import requests
import yaml
import paramiko
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from parser_utils import parse_batch_input, parse_share_link, proxy_to_share_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fnos-node-hub")

app = FastAPI(title="FnOS Mihomo & Clash Node Hub", version="1.0.0")

# Default Connection Settings
SERVER_SETTINGS = {
    "ssh_host": "192.168.1.57",
    "ssh_port": 22,
    "ssh_user": "admin",
    "ssh_pass": "Wzdsrs0301",
    "remote_path": "/vol1/1000/Docker/mihomo/config/config.yaml",
    "clash_path": "/vol1/1000/Docker/clash/clash.yml",
    "mihomo_api": "http://192.168.1.57:9092",
    "mihomo_secret": "Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n",
    "docker_container": "mihomo"
}

def get_ssh_client():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=SERVER_SETTINGS["ssh_host"],
        port=int(SERVER_SETTINGS["ssh_port"]),
        username=SERVER_SETTINGS["ssh_user"],
        password=SERVER_SETTINGS["ssh_pass"],
        timeout=8
    )
    return ssh

def execute_remote_cmd(cmd: str, use_sudo: bool = True) -> tuple[int, str, str]:
    ssh = get_ssh_client()
    try:
        if use_sudo:
            full_cmd = f"echo '{SERVER_SETTINGS['ssh_pass']}' | sudo -S -p '' {cmd}"
        else:
            full_cmd = cmd
        stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, out, err
    finally:
        ssh.close()

def read_remote_file(path: str) -> str:
    ssh = get_ssh_client()
    try:
        sftp = ssh.open_sftp()
        with sftp.open(path, "r") as f:
            content = f.read().decode('utf-8', errors='ignore')
        sftp.close()
        return content
    except Exception as e:
        # Fallback to sudo cat
        cmd = f"cat '{path}'"
        code, out, err = execute_remote_cmd(cmd, use_sudo=True)
        if code == 0:
            return out
        raise HTTPException(status_code=500, detail=f"Failed to read file {path}: {str(e)} | {err}")
    finally:
        ssh.close()

def write_remote_file(path: str, content: str):
    ssh = get_ssh_client()
    try:
        # Backup original file first
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}.bak_{ts}"
        execute_remote_cmd(f"cp '{path}' '{backup_path}'", use_sudo=True)

        # Write to tmp file then move with sudo
        tmp_remote = f"/tmp/config_upload_{ts}.yaml"
        sftp = ssh.open_sftp()
        with sftp.open(tmp_remote, "w") as f:
            f.write(content)
        sftp.close()

        # Move to target path and adjust permissions
        code, out, err = execute_remote_cmd(f"mv '{tmp_remote}' '{path}' && chmod 666 '{path}'", use_sudo=True)
        if code != 0:
            raise HTTPException(status_code=500, detail=f"Failed to overwrite {path}: {err}")
    finally:
        ssh.close()

def reload_mihomo_core() -> dict:
    """Trigger Mihomo API reload config, or fallback to restart docker container."""
    api_url = SERVER_SETTINGS["mihomo_api"].rstrip("/")
    secret = SERVER_SETTINGS["mihomo_secret"]
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
    
    # Try PUT /configs
    try:
        resp = requests.put(
            f"{api_url}/configs?force=true",
            headers=headers,
            json={"path": "", "payload": ""},
            timeout=5
        )
        if resp.status_code in [200, 204]:
            return {"success": True, "method": "api_reload", "message": "Mihomo 核心配置已热重载成功！"}
    except Exception as ex:
        logger.warning(f"API reload failed: {ex}")

    # Fallback to docker restart
    container = SERVER_SETTINGS.get("docker_container", "mihomo")
    code, out, err = execute_remote_cmd(f"docker restart {container}", use_sudo=True)
    if code == 0:
        return {"success": True, "method": "docker_restart", "message": f"Mihomo 容器 {container} 重启成功！"}
    else:
        return {"success": False, "method": "failed", "message": f"热重载及容器重启均失败: {err}"}

# ==================== API ROUTES ====================

@app.get("/api/settings")
def get_settings():
    return SERVER_SETTINGS

@app.post("/api/settings")
def update_settings(settings: dict = Body(...)):
    for k, v in settings.items():
        if k in SERVER_SETTINGS:
            SERVER_SETTINGS[k] = v
    return {"success": True, "settings": SERVER_SETTINGS}

@app.get("/api/status")
def get_system_status():
    status = {
        "ssh_connected": False,
        "mihomo_running": False,
        "mihomo_api_ready": False,
        "mihomo_version": "",
        "config_file_exists": False,
        "config_path": SERVER_SETTINGS["remote_path"],
        "error": None
    }
    # Test SSH
    try:
        code, out, _ = execute_remote_cmd("docker ps --filter 'name=mihomo' --format '{{.Status}}'")
        status["ssh_connected"] = (code == 0)
        status["mihomo_running"] = bool("Up" in out)
    except Exception as e:
        status["error"] = str(e)
        return status

    # Test Mihomo API
    try:
        api_url = SERVER_SETTINGS["mihomo_api"].rstrip("/")
        secret = SERVER_SETTINGS["mihomo_secret"]
        headers = {"Authorization": f"Bearer {secret}"}
        resp = requests.get(f"{api_url}/version", headers=headers, timeout=3)
        if resp.status_code == 200:
            status["mihomo_api_ready"] = True
            vdata = resp.json()
            status["mihomo_version"] = vdata.get("version", "Active")
    except Exception:
        status["mihomo_api_ready"] = False

    # Test config file
    try:
        code, out, _ = execute_remote_cmd(f"test -f '{SERVER_SETTINGS['remote_path']}' && echo 'exists'")
        status["config_file_exists"] = ("exists" in out)
    except Exception:
        pass

    return status

@app.get("/api/config")
def get_config(target: str = Query("mihomo", enum=["mihomo", "clash"])):
    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]
    raw_content = read_remote_file(path)
    
    try:
        parsed = yaml.safe_load(raw_content) or {}
    except Exception as e:
        parsed = {}
        logger.error(f"YAML parse error: {e}")

    proxies = parsed.get("proxies", [])
    if not isinstance(proxies, list):
        proxies = []

    proxy_groups = parsed.get("proxy-groups", [])
    if not isinstance(proxy_groups, list):
        proxy_groups = []

    rules = parsed.get("rules", [])
    if not isinstance(rules, list):
        rules = []

    # Attach export share link to each proxy
    for p in proxies:
        if isinstance(p, dict):
            p["_share_link"] = proxy_to_share_link(p)

    return {
        "success": True,
        "target": target,
        "path": path,
        "proxies": proxies,
        "proxy_groups": proxy_groups,
        "rules": rules,
        "raw_yaml": raw_content,
        "total_proxies": len(proxies),
        "total_groups": len(proxy_groups),
        "total_rules": len(rules)
    }

@app.post("/api/config/save-raw")
def save_raw_config(payload: dict = Body(...)):
    raw_yaml = payload.get("raw_yaml", "")
    target = payload.get("target", "mihomo")
    auto_reload = payload.get("auto_reload", True)

    if not raw_yaml.strip():
        raise HTTPException(status_code=400, detail="配置内容不能为空！")

    # Validate YAML
    try:
        yaml.safe_load(raw_yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"YAML 语法格式错误: {str(e)}")

    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]
    write_remote_file(path, raw_yaml)

    reload_result = None
    if auto_reload and target == "mihomo":
        reload_result = reload_mihomo_core()

    return {
        "success": True,
        "message": "配置保存成功！",
        "reload": reload_result
    }

@app.post("/api/proxies/save-all")
def save_all_proxies(payload: dict = Body(...)):
    """Save full list of proxies, sync proxy groups, and write to YAML."""
    proxies = payload.get("proxies", [])
    proxy_groups = payload.get("proxy_groups", [])
    rules = payload.get("rules", None)
    auto_reload = payload.get("auto_reload", True)
    target = payload.get("target", "mihomo")
    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]

    raw_content = read_remote_file(path)
    try:
        config_dict = yaml.safe_load(raw_content) or {}
    except Exception:
        config_dict = {}

    # Clean internal helper keys before saving
    cleaned_proxies = []
    for p in proxies:
        cp = {k: v for k, v in p.items() if not k.startswith("_")}
        cleaned_proxies.append(cp)

    config_dict["proxies"] = cleaned_proxies

    if proxy_groups:
        cleaned_groups = []
        for g in proxy_groups:
            cg = {k: v for k, v in g.items() if not k.startswith("_")}
            cleaned_groups.append(cg)
        config_dict["proxy-groups"] = cleaned_groups

    if rules is not None:
        config_dict["rules"] = rules

    # Dump yaml with utf-8
    new_yaml = yaml.dump(config_dict, allow_unicode=True, sort_keys=False, default_flow_style=False)
    write_remote_file(path, new_yaml)

    reload_result = None
    if auto_reload and target == "mihomo":
        reload_result = reload_mihomo_core()

    return {
        "success": True,
        "message": f"成功保存 {len(cleaned_proxies)} 个代理节点！",
        "reload": reload_result
    }

@app.post("/api/proxies/add")
def add_proxy(payload: dict = Body(...)):
    proxy = payload.get("proxy", {})
    auto_reload = payload.get("auto_reload", True)
    add_to_groups = payload.get("add_to_groups", ["PROXY"])
    target = payload.get("target", "mihomo")

    if not proxy or not proxy.get("name") or not proxy.get("server"):
        raise HTTPException(status_code=400, detail="节点名称和服务器地址不能为空！")

    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]
    raw_content = read_remote_file(path)
    config_dict = yaml.safe_load(raw_content) or {}

    proxies = config_dict.get("proxies", [])
    if not isinstance(proxies, list):
        proxies = []

    # Clean helper keys
    clean_proxy = {k: v for k, v in proxy.items() if not k.startswith("_")}

    # Check for duplicate names
    for existing in proxies:
        if existing.get("name") == clean_proxy.get("name"):
            raise HTTPException(status_code=400, detail=f"已存在同名节点: {clean_proxy.get('name')}")

    proxies.append(clean_proxy)
    config_dict["proxies"] = proxies

    # Add to groups
    if add_to_groups:
        groups = config_dict.get("proxy-groups", [])
        for g in groups:
            if g.get("name") in add_to_groups:
                g_proxies = g.get("proxies", [])
                if clean_proxy["name"] not in g_proxies:
                    # Insert before DIRECT if present
                    if "DIRECT" in g_proxies:
                        idx = g_proxies.index("DIRECT")
                        g_proxies.insert(idx, clean_proxy["name"])
                    else:
                        g_proxies.append(clean_proxy["name"])
                g["proxies"] = g_proxies

    new_yaml = yaml.dump(config_dict, allow_unicode=True, sort_keys=False, default_flow_style=False)
    write_remote_file(path, new_yaml)

    reload_result = None
    if auto_reload and target == "mihomo":
        reload_result = reload_mihomo_core()

    return {"success": True, "message": f"节点【{clean_proxy['name']}】添加成功！", "reload": reload_result}

@app.post("/api/proxies/batch-import")
def batch_import_proxies(payload: dict = Body(...)):
    raw_text = payload.get("text", "")
    add_to_groups = payload.get("add_to_groups", ["PROXY"])
    auto_reload = payload.get("auto_reload", True)
    target = payload.get("target", "mihomo")

    imported = parse_batch_input(raw_text)
    if not imported:
        raise HTTPException(status_code=400, detail="未能解析出有效的节点，请检查输入格式（支持 vless://, vmess://, trojan://, ss://, hy2:// 或 YAML 节点列表）")

    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]
    raw_content = read_remote_file(path)
    config_dict = yaml.safe_load(raw_content) or {}

    proxies = config_dict.get("proxies", [])
    if not isinstance(proxies, list):
        proxies = []

    existing_names = {p.get("name") for p in proxies if isinstance(p, dict)}
    added_names = []
    
    for p in imported:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        # Ensure unique name
        orig_name = p.get("name")
        name = orig_name
        counter = 1
        while name in existing_names:
            name = f"{orig_name}-{counter}"
            counter += 1
        p["name"] = name
        existing_names.add(name)
        
        clean_p = {k: v for k, v in p.items() if not k.startswith("_")}
        proxies.append(clean_p)
        added_names.append(name)

    config_dict["proxies"] = proxies

    # Add to groups
    if add_to_groups and added_names:
        groups = config_dict.get("proxy-groups", [])
        for g in groups:
            if g.get("name") in add_to_groups:
                g_proxies = g.get("proxies", [])
                for aname in added_names:
                    if aname not in g_proxies:
                        if "DIRECT" in g_proxies:
                            idx = g_proxies.index("DIRECT")
                            g_proxies.insert(idx, aname)
                        else:
                            g_proxies.append(aname)
                g["proxies"] = g_proxies

    new_yaml = yaml.dump(config_dict, allow_unicode=True, sort_keys=False, default_flow_style=False)
    write_remote_file(path, new_yaml)

    reload_result = None
    if auto_reload and target == "mihomo":
        reload_result = reload_mihomo_core()

    return {
        "success": True,
        "count": len(added_names),
        "names": added_names,
        "message": f"成功导入 {len(added_names)} 个节点！",
        "reload": reload_result
    }

@app.post("/api/subscription/fetch")
def fetch_subscription(payload: dict = Body(...)):
    sub_url = payload.get("url", "").strip()
    user_agent = payload.get("user_agent", "ClashMeta")
    if not sub_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请输入有效的 HTTP/HTTPS 订阅链接")

    try:
        headers = {
            "User-Agent": user_agent or "ClashMeta"
        }
        resp = requests.get(sub_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"下载订阅失败: HTTP {resp.status_code}")
        
        content = resp.text
        proxies = parse_batch_input(content)
        return {
            "success": True,
            "count": len(proxies),
            "proxies": proxies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"订阅解析失败: {str(e)}")

@app.get("/api/proxies/delay")
def test_node_delay(name: str = Query(...)):
    api_url = SERVER_SETTINGS["mihomo_api"].rstrip("/")
    secret = SERVER_SETTINGS["mihomo_secret"]
    headers = {"Authorization": f"Bearer {secret}"}

    encoded_name = urllib.parse.quote(name)
    test_url = f"{api_url}/proxies/{encoded_name}/delay?url=http://www.gstatic.com/generate_204&timeout=3000"

    try:
        resp = requests.get(test_url, headers=headers, timeout=4)
        data = resp.json()
        if "delay" in data:
            return {"success": True, "name": name, "delay": data["delay"]}
        else:
            return {"success": False, "name": name, "error": data.get("message", "Timeout/Error")}
    except Exception as e:
        return {"success": False, "name": name, "error": str(e)}

@app.get("/api/backups")
def list_backups(target: str = Query("mihomo", enum=["mihomo", "clash"])):
    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]
    dir_path = os.path.dirname(path)
    base_name = os.path.basename(path)

    cmd = f"ls -la --time-style=+'%Y-%m-%d %H:%M:%S' '{dir_path}'/{base_name}.bak* 2>/dev/null"
    code, out, _ = execute_remote_cmd(cmd)
    
    backups = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 8:
            filepath = parts[-1]
            size = parts[4]
            dt = f"{parts[5]} {parts[6]}"
            backups.append({
                "path": filepath,
                "filename": os.path.basename(filepath),
                "size": f"{int(size)/1024:.1f} KB" if size.isdigit() else size,
                "time": dt
            })
    
    # Sort newest first
    backups.reverse()
    return {"success": True, "backups": backups}

@app.post("/api/backups/restore")
def restore_backup(payload: dict = Body(...)):
    backup_path = payload.get("backup_path", "")
    target = payload.get("target", "mihomo")
    path = SERVER_SETTINGS["remote_path"] if target == "mihomo" else SERVER_SETTINGS["clash_path"]

    if not backup_path:
        raise HTTPException(status_code=400, detail="备份文件路径不能为空")

    code, out, err = execute_remote_cmd(f"cp '{backup_path}' '{path}' && chmod 666 '{path}'", use_sudo=True)
    if code != 0:
        raise HTTPException(status_code=500, detail=f"恢复备份失败: {err}")

    reload_result = None
    if target == "mihomo":
        reload_result = reload_mihomo_core()

    return {"success": True, "message": "备份恢复成功！", "reload": reload_result}

@app.post("/api/mihomo/restart")
def restart_mihomo():
    container = SERVER_SETTINGS.get("docker_container", "mihomo")
    code, out, err = execute_remote_cmd(f"docker restart {container}", use_sudo=True)
    if code == 0:
        return {"success": True, "message": f"容器 {container} 重启成功！"}
    else:
        raise HTTPException(status_code=500, detail=f"重启容器失败: {err}")

# Mount Static Files
static_dir = os.path.join(current_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def index():
    index_file = os.path.join(current_dir, "static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>FnOS Node Hub Running</h1>")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print(">> FnOS Mihomo & Clash Node Hub Started Successfully!")
    print(">> Local Web URL: http://127.0.0.1:8899")
    print("="*60 + "\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8899, reload=False)

