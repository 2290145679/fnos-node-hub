import base64
import json
import re
import urllib.parse
import yaml

def safe_b64decode(s: str) -> str:
    s = s.strip()
    s = s.replace('-', '+').replace('_', '/')
    padding = len(s) % 4
    if padding != 0:
        s += '=' * (4 - padding)
    try:
        return base64.b64decode(s).decode('utf-8', errors='ignore')
    except Exception:
        try:
            return base64.b64decode(s).decode('gbk', errors='ignore')
        except Exception:
            return ""

def parse_vless(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    uuid = parsed.username or ""
    server = parsed.hostname or ""
    port = parsed.port or 443
    name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"vless-{server}:{port}"
    query = urllib.parse.parse_qs(parsed.query)

    security = query.get('security', [''])[0]
    network = query.get('type', ['tcp'])[0]
    flow = query.get('flow', [''])[0]
    sni = query.get('sni', query.get('peer', ['']))[0]
    fp = query.get('fp', [''])[0]
    pbk = query.get('pbk', [''])[0]
    sid = query.get('sid', [''])[0]
    path = query.get('path', [''])[0]
    service_name = query.get('serviceName', [''])[0]

    proxy = {
        "name": name,
        "type": "vless",
        "server": server,
        "port": int(port),
        "uuid": uuid,
        "network": network,
        "udp": True,
    }

    if flow:
        proxy["flow"] = flow

    if security == "reality":
        proxy["tls"] = True
        reality_opts = {}
        if pbk:
            reality_opts["public-key"] = pbk
        if sid:
            reality_opts["short-id"] = sid
        proxy["reality-opts"] = reality_opts
        if sni:
            proxy["servername"] = sni
        if fp:
            proxy["client-fingerprint"] = fp
    elif security == "tls":
        proxy["tls"] = True
        if sni:
            proxy["servername"] = sni
        if fp:
            proxy["client-fingerprint"] = fp

    if network == "ws":
        ws_opts = {}
        if path:
            ws_opts["path"] = path
        headers = {}
        host = query.get('host', [''])[0]
        if host:
            headers["Host"] = host
        if headers:
            ws_opts["headers"] = headers
        proxy["ws-opts"] = ws_opts
    elif network == "grpc":
        grpc_opts = {}
        if service_name:
            grpc_opts["grpc-service-name"] = service_name
        proxy["grpc-opts"] = grpc_opts

    return proxy

def parse_vmess(url: str) -> dict:
    raw = url[len("vmess://"):]
    decoded = safe_b64decode(raw)
    if not decoded:
        return {}
    try:
        data = json.loads(decoded)
    except Exception:
        return {}

    name = data.get("ps", f"vmess-{data.get('add', '')}:{data.get('port', '')}")
    server = data.get("add", "")
    port = int(data.get("port", 443))
    uuid = data.get("id", "")
    aid = int(data.get("aid", 0))
    net = data.get("net", "tcp")
    tls = (data.get("tls", "") == "tls")
    sni = data.get("sni", "") or data.get("host", "")

    proxy = {
        "name": name,
        "type": "vmess",
        "server": server,
        "port": port,
        "uuid": uuid,
        "alterId": aid,
        "cipher": "auto",
        "udp": True,
        "network": net,
        "tls": tls
    }
    if tls and sni:
        proxy["servername"] = sni

    if net == "ws":
        ws_opts = {}
        path = data.get("path", "")
        if path:
            ws_opts["path"] = path
        host = data.get("host", "")
        if host:
            ws_opts["headers"] = {"Host": host}
        proxy["ws-opts"] = ws_opts
    elif net == "grpc":
        service_name = data.get("path", "")
        if service_name:
            proxy["grpc-opts"] = {"grpc-service-name": service_name}

    return proxy

def parse_trojan(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    password = parsed.username or ""
    server = parsed.hostname or ""
    port = parsed.port or 443
    name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"trojan-{server}:{port}"
    query = urllib.parse.parse_qs(parsed.query)

    sni = query.get('sni', query.get('peer', ['']))[0]
    network = query.get('type', ['tcp'])[0]

    proxy = {
        "name": name,
        "type": "trojan",
        "server": server,
        "port": int(port),
        "password": password,
        "udp": True,
        "network": network
    }
    if sni:
        proxy["sni"] = sni

    return proxy

def parse_ss(url: str) -> dict:
    raw = url[len("ss://"):]
    fragment = ""
    if "#" in raw:
        raw, fragment = raw.split("#", 1)
        fragment = urllib.parse.unquote(fragment)

    if "@" in raw:
        user_info, host_port = raw.split("@", 1)
        decoded_user = safe_b64decode(user_info)
        if ":" in decoded_user:
            method, password = decoded_user.split(":", 1)
        else:
            method, password = "aes-256-gcm", decoded_user
        
        host_port_parts = host_port.split(":")
        server = host_port_parts[0]
        port = int(host_port_parts[1].split("/")[0]) if len(host_port_parts) > 1 else 8388
    else:
        decoded = safe_b64decode(raw)
        match = re.match(r"^(.+?):(.*)@(.+?):(\d+)$", decoded)
        if match:
            method, password, server, port = match.groups()
            port = int(port)
        else:
            return {}

    name = fragment if fragment else f"ss-{server}:{port}"
    return {
        "name": name,
        "type": "ss",
        "server": server,
        "port": port,
        "cipher": method,
        "password": password,
        "udp": True
    }

def parse_hysteria2(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    auth = parsed.username or ""
    server = parsed.hostname or ""
    port = parsed.port or 443
    name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"hy2-{server}:{port}"
    query = urllib.parse.parse_qs(parsed.query)

    sni = query.get('sni', [''])[0]
    insecure = query.get('insecure', ['0'])[0] == '1'
    obfs = query.get('obfs', [''])[0]
    obfs_password = query.get('obfs-password', [''])[0]

    proxy = {
        "name": name,
        "type": "hysteria2",
        "server": server,
        "port": int(port),
        "auth": auth,
        "udp": True
    }
    if sni:
        proxy["sni"] = sni
    if insecure:
        proxy["skip-cert-verify"] = True
    if obfs:
        proxy["obfs"] = obfs
        if obfs_password:
            proxy["obfs-password"] = obfs_password

    return proxy

def parse_share_link(link: str) -> dict:
    link = link.strip()
    if link.startswith("vless://"):
        return parse_vless(link)
    elif link.startswith("vmess://"):
        return parse_vmess(link)
    elif link.startswith("trojan://"):
        return parse_trojan(link)
    elif link.startswith("ss://"):
        return parse_ss(link)
    elif link.startswith("hysteria2://") or link.startswith("hy2://"):
        return parse_hysteria2(link)
    return {}

def parse_batch_input(text: str) -> list:
    text = text.strip()
    if not text:
        return []

    # 1. Try if text is base64 encoded subscription
    if not ("\n" in text) and len(text) > 40 and not text.startswith(("vless://", "vmess://", "trojan://", "ss://", "hy")):
        decoded = safe_b64decode(text)
        if any(proto in decoded for proto in ["vless://", "vmess://", "trojan://", "ss://", "hysteria2://"]):
            text = decoded

    # 2. Try parsing as Clash / Mihomo YAML
    if ("proxies:" in text) or text.startswith("- name:"):
        try:
            parsed_yaml = yaml.safe_load(text)
            if isinstance(parsed_yaml, dict) and "proxies" in parsed_yaml:
                return parsed_yaml["proxies"]
            elif isinstance(parsed_yaml, list):
                return parsed_yaml
        except Exception:
            pass

    # 3. Parse line by line
    results = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        proxy = parse_share_link(line)
        if proxy and proxy.get("name"):
            results.append(proxy)
    return results

def proxy_to_share_link(proxy: dict) -> str:
    ptype = proxy.get("type", "").lower()
    name = urllib.parse.quote(proxy.get("name", ""))
    server = proxy.get("server", "")
    port = proxy.get("port", 443)

    if ptype == "vless":
        uuid = proxy.get("uuid", "")
        params = []
        flow = proxy.get("flow", "")
        if flow:
            params.append(f"flow={flow}")
        
        network = proxy.get("network", "tcp")
        params.append(f"type={network}")

        if proxy.get("tls"):
            reality = proxy.get("reality-opts")
            if reality:
                params.append("security=reality")
                if reality.get("public-key"):
                    params.append(f"pbk={reality.get('public-key')}")
                if reality.get("short-id"):
                    params.append(f"sid={reality.get('short-id')}")
            else:
                params.append("security=tls")
            
            if proxy.get("servername"):
                params.append(f"sni={proxy.get('servername')}")
            if proxy.get("client-fingerprint"):
                params.append(f"fp={proxy.get('client-fingerprint')}")
        else:
            params.append("security=none")

        query_str = ("?" + "&".join(params)) if params else ""
        return f"vless://{uuid}@{server}:{port}{query_str}#{name}"

    elif ptype == "vmess":
        vdata = {
            "v": "2",
            "ps": proxy.get("name", ""),
            "add": server,
            "port": port,
            "id": proxy.get("uuid", ""),
            "aid": proxy.get("alterId", 0),
            "scy": proxy.get("cipher", "auto"),
            "net": proxy.get("network", "tcp"),
            "type": "none",
            "tls": "tls" if proxy.get("tls") else ""
        }
        if proxy.get("servername"):
            vdata["sni"] = proxy.get("servername")
        raw = json.dumps(vdata).encode('utf-8')
        return "vmess://" + base64.b64encode(raw).decode('utf-8')

    elif ptype == "trojan":
        password = proxy.get("password", "")
        sni = proxy.get("sni", "")
        query_str = f"?sni={sni}" if sni else ""
        return f"trojan://{password}@{server}:{port}{query_str}#{name}"

    elif ptype == "ss":
        cipher = proxy.get("cipher", "aes-256-gcm")
        password = proxy.get("password", "")
        user_info = f"{cipher}:{password}"
        b64_user = base64.b64encode(user_info.encode('utf-8')).decode('utf-8')
        return f"ss://{b64_user}@{server}:{port}#{name}"

    elif ptype == "hysteria2":
        auth = proxy.get("auth", "")
        params = []
        if proxy.get("sni"):
            params.append(f"sni={proxy.get('sni')}")
        if proxy.get("skip-cert-verify"):
            params.append("insecure=1")
        query_str = ("?" + "&".join(params)) if params else ""
        return f"hysteria2://{auth}@{server}:{port}{query_str}#{name}"

    return ""
