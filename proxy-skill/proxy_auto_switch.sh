#!/bin/bash
# ============================================================
# proxy_auto_switch.sh — 代理节点自动切换
# 用途：当当前节点 IP 被封 / 失效时，从订阅中自动找可用节点
# 用法：bash /opt/data/proxy-skill/proxy_auto_switch.sh [--node us05]
#   --node <名> 优先尝试指定节点
# ============================================================
set -u
SKILL_DIR="/opt/data/proxy-skill"
source "$SKILL_DIR/subscription.conf" 2>/dev/null

SB="$SKILL_DIR/sing-box"
PIDFILE="$SKILL_DIR/sing-box.pid"
LOGFILE="$SKILL_DIR/sing-box.log"

echo "=== 代理节点自动切换 ==="

# 1. 下载订阅并解析节点列表（缓存）
curl -s --max-time 30 "$SUBSCRIPTION_URL" -o /tmp/sub_raw.txt
python3 - "$NODE_LIST_FILE" << 'PYEOF'
import base64, sys, re, urllib.parse
out = sys.argv[1]
data = open('/tmp/sub_raw.txt','rb').read()
try:
    decoded = base64.b64decode(data).decode()
except Exception:
    decoded = data.decode(errors='ignore')
lines = [l for l in decoded.splitlines() if l.strip()]
with open('/tmp/sub_decoded.txt', 'w') as f:
    f.write('\n'.join(lines))
with open(out, 'w') as f:
    for i, line in enumerate(lines):
        m = re.match(r'^(vless|vmess|trojan|hysteria2|hy2)://', line)
        if not m: continue
        proto = m.group(1)
        name = urllib.parse.unquote(line.split('#',1)[1]).split('|')[0].strip() if '#' in line else f'node{i}'
        # 提取 server
        try:
            if proto == 'vless':
                info = line.split('://')[1].split('?')[0]
                server = info.split('@')[1].split(':')[0]
            elif proto == 'hysteria2' or proto == 'hy2':
                info = line.split('://')[1].split('?')[0]
                server = info.split('@')[1].split(':')[0]
            elif proto == 'vmess':
                import json
                info = json.loads(base64.b64decode(line.split('://')[1]).decode())
                server = info.get('add','?')
            else:
                server = '?'
        except Exception:
            server = '?'
        f.write(f'{i}|{proto}|{server}|{name}\n')
print(f"解析完成: {len(lines)} 行")
PYEOF

# 2. 测试指定节点或当前节点是否可用
test_node() {
    # $1 = server, $2 = config_file
    local cfg="$2"
    $SB check -c "$cfg" 2>/dev/null || return 1
    # 启动临时实例测试（独立端口）
    local port=$(( 21900 + RANDOM % 50 ))
    python3 -c "
import json
cfg = json.load(open('$cfg'))
cfg['inbounds'][0]['listen_port'] = $port
json.dump(cfg, open('/tmp/probe_$port.json','w'))
"
    $SB run -c /tmp/probe_$port.json > /tmp/probe_$port.log 2>&1 &
    local spid=$!
    sleep 3
    local code=$(curl -s --max-time 10 --proxy http://127.0.0.1:$port \
        -A "Mozilla/5.0" -o /dev/null -w "%{http_code}" "$JAVDB_TEST_URL" 2>/dev/null)
    kill $spid 2>/dev/null
    wait $spid 2>/dev/null
    rm -f /tmp/probe_$port.json /tmp/probe_$port.log
    if [ "$code" = "200" ] || [ "$code" = "302" ]; then
        echo "OK"
        return 0
    else
        echo "FAIL($code)"
        return 1
    fi
}

# 3. 主流程
# 3a. 先试 --node 指定的节点
REQUESTED_NODE=""
if [ "${1:-}" = "--node" ] && [ -n "${2:-}" ]; then
    REQUESTED_NODE="$2"
fi

# 3b. 找对应节点配置文件
CANDIDATES=""
if [ -n "$REQUESTED_NODE" ]; then
    # 用户指定节点（如 us05）→ 先映射到订阅节点名
    python3 - "$REQUESTED_NODE" << 'PYEOF'
import sys, base64, re, urllib.parse, json
target = sys.argv[1]
data = open('/tmp/sub_raw.txt','rb').read()
try:
    decoded = base64.b64decode(data).decode()
except Exception:
    decoded = data.decode(errors='ignore')
lines = [l for l in decoded.splitlines() if l.strip()]
# 映射表：us01→圣何塞01, us05→圣何塞05 等
# 用户常说的 usXX = 美国圣何塞 XX
us_map = {}
for i, line in enumerate(lines):
    full_name = urllib.parse.unquote(line.split('#',1)[1]) if '#' in line else ''
    name = full_name.split('|')[0].strip()
    # 只映射 IP 直连的圣何塞节点（"三网推荐"组，REALITY 协议）
    if '圣何塞' in name and '三网推荐' in full_name:
        m = re.search(r'圣何塞(\d+)', name)
        if m:
            us_map[f'us{int(m.group(1)):02d}'] = i
    # 备选：任何圣何塞节点（无三网推荐标注时兜底）
    if '圣何塞' in name and f'us{int(re.search(r"圣何塞(\d+)", name).group(1)):02d}' not in us_map:
        m = re.search(r'圣何塞(\d+)', name)
        if m:
            us_map.setdefault(f'us{int(m.group(1)):02d}', i)

# 匹配：精确名 > usXX 映射 > 模糊包含
idx = None
for i, line in enumerate(lines):
    name = urllib.parse.unquote(line.split('#',1)[1]).split('|')[0].strip() if '#' in line else ''
    if target.lower() == name.lower():
        idx = i
        break
if idx is None and target.lower() in us_map:
    idx = us_map[target.lower()]
if idx is None:
    for i, line in enumerate(lines):
        name = urllib.parse.unquote(line.split('#',1)[1]).split('|')[0].strip() if '#' in line else ''
        if target.lower() in name.lower() or target.lower() in line.lower():
            idx = i
            break
if idx is None:
    print("NOT_FOUND")
    sys.exit(1)
print(f"MATCH:{idx}")
PYEOF
    MATCH_IDX=$(python3 - "$REQUESTED_NODE" 2>/dev/null << 'PYEOF'
import sys, base64, re, urllib.parse
target = sys.argv[1]
data = open('/tmp/sub_raw.txt','rb').read()
try:
    decoded = base64.b64decode(data).decode()
except Exception:
    decoded = data.decode(errors='ignore')
lines = [l for l in decoded.splitlines() if l.strip()]
us_map = {}
for i, line in enumerate(lines):
    full_name = urllib.parse.unquote(line.split('#',1)[1]) if '#' in line else ''
    name = full_name.split('|')[0].strip()
    if '圣何塞' in name and '三网推荐' in full_name:
        m = re.search(r'圣何塞(\d+)', name)
        if m: us_map[f'us{int(m.group(1)):02d}'] = i
    if '圣何塞' in name and f'us{int(re.search(r"圣何塞(\d+)", name).group(1)):02d}' not in us_map:
        m = re.search(r'圣何塞(\d+)', name)
        if m: us_map.setdefault(f'us{int(m.group(1)):02d}', i)
for i, line in enumerate(lines):
    name = urllib.parse.unquote(line.split('#',1)[1]).split('|')[0].strip() if '#' in line else ''
    if target.lower() == name.lower():
        print(i); break
else:
    if target.lower() in us_map:
        print(us_map[target.lower()])
    else:
        print(-1)
PYEOF
)
    if [ "$MATCH_IDX" = "-1" ] || [ -z "$MATCH_IDX" ]; then
        echo "⚠️ 订阅中未找到节点 $REQUESTED_NODE"
    else
        NODE_LINE=$(sed -n "$((MATCH_IDX+1))p" /tmp/sub_decoded.txt)
        echo "→ 节点 $REQUESTED_NODE = 订阅第 ${MATCH_IDX} 行"
        # 生成该节点的 sing-box 配置
        CFG_RESULT=$(python3 - "$REQUESTED_NODE" "$NODE_LINE" 2>/dev/null << 'PYEOF'
import sys, base64, re, urllib.parse, json
target, line = sys.argv[1], sys.argv[2]
if not line.startswith('vless://'):
    print("UNSUPPORTED"); sys.exit(1)
core = line.split('://')[1]
params_part = core.split('?')[1] if '?' in core else ''
auth_server = core.split('?')[0]
uuid, server_port = auth_server.split('@')
server, port = server_port.split(':')
params = dict(p.split('=',1) for p in params_part.split('&') if '=' in p)
outbound = {"type": "vless", "tag": target, "server": server, "server_port": int(port), "uuid": uuid}
if params.get('security') == 'reality':
    outbound["flow"] = urllib.parse.unquote(params.get('flow','xtls-rprx-vision'))
    outbound["tls"] = {"enabled": True, "server_name": params.get('sni',server),
        "reality": {"enabled": True, "public_key": urllib.parse.unquote(params.get('pbk','')), "short_id": urllib.parse.unquote(params.get('sid','')).split('#')[0]},
        "utls": {"enabled": True, "fingerprint": urllib.parse.unquote(params.get('fp','chrome'))}}
elif params.get('security') == 'tls':
    outbound["tls"] = {"enabled": True, "server_name": urllib.parse.unquote(params.get('sni',server)), "insecure": True}
if params.get('type') == 'ws':
    outbound["transport"] = {"type": "ws", "path": params.get('path',''), "headers": {"Host": params.get('host','')}}
cfg = {"log": {"level": "error"},
    "inbounds": [{"type": "mixed", "listen": "127.0.0.1", "listen_port": 10808}],
    "outbounds": [outbound]}
outfile = f"/opt/data/proxy-skill/node_{target}.json"
json.dump(cfg, open(outfile,'w'), ensure_ascii=False)
print(f"OK:{outfile}")
PYEOF
)
        if [[ "$CFG_RESULT" == OK:* ]]; then
            CFG_FILE="${CFG_RESULT#OK:}"
            echo "→ 测试指定节点 $REQUESTED_NODE ..."
            if test_node "$REQUESTED_NODE" "$CFG_FILE" | grep -q OK; then
                echo "✅ $REQUESTED_NODE 可用，切换中..."
                cp "$CFG_FILE" "$SKILL_DIR/reality_active.json"
                sed -i "s|CONFIG=.*|CONFIG=$SKILL_DIR/reality_active.json|" "$SKILL_DIR/proxy.sh"
                bash "$SKILL_DIR/proxy.sh" restart 2>&1 | tail -1
                sed -i "s|LAST_GOOD_NODE=.*|LAST_GOOD_NODE=\"$REQUESTED_NODE\"|" "$SKILL_DIR/subscription.conf"
                echo "✅ 已切换到 $REQUESTED_NODE"
                exit 0
            fi
            echo "⚠️ $REQUESTED_NODE 不可用，继续尝试其他节点"
        else
            echo "⚠️ 配置生成失败: $CFG_RESULT"
        fi
    fi
fi

# 3c. 遍历订阅所有节点（优先圣何塞直连 IP）测试
echo "→ 遍历订阅节点测试..."
python3 << 'PYEOF' > /tmp/auto_switch_candidates.txt
import base64, re, urllib.parse
data = open('/tmp/sub_raw.txt','rb').read()
try:
    decoded = base64.b64decode(data).decode()
except Exception:
    decoded = data.decode(errors='ignore')
lines = [l for l in decoded.splitlines() if l.strip()]
# 优先级：含"圣何塞"且IP直连 > 含"圣何塞" > 其他
def score(line):
    name = line.split('#',1)[1] if '#' in line else ''
    if '圣何塞' in name and re.match(r'vless://[^@]+@\d+\.\d+\.\d+\.\d+', line): return 0
    if '圣何塞' in name: return 1
    if '美国' in name: return 2
    return 3
for i, line in enumerate(sorted(lines, key=score)):
    m = re.match(r'^(vless|vmess|trojan|hysteria2|hy2)://', line)
    if not m: continue
    name = urllib.parse.unquote(line.split('#',1)[1]).split('|')[0].strip() if '#' in line else f'node{i}'
    print(f'{i}|{name}|{line}')
PYEOF

while IFS='|' read -r idx name link; do
    [ -z "$link" ] && continue
    echo "→ 测试 [$idx] $name ..."
    # 生成配置（复用上面的生成逻辑）
    CFG_OUT=$(python3 - "$name" 2>/dev/null << 'PYEOF'
import sys, base64, re, urllib.parse, json
target = sys.argv[1]
data = open('/tmp/sub_raw.txt','rb').read()
try:
    decoded = base64.b64decode(data).decode()
except Exception:
    decoded = data.decode(errors='ignore')
lines = [l for l in decoded.splitlines() if l.strip()]
for line in lines:
    name = urllib.parse.unquote(line.split('#',1)[1]).split('|')[0].strip() if '#' in line else ''
    if target == name:
        if line.startswith('vless://'):
            core = line.split('://')[1]
            params_part = core.split('?')[1] if '?' in core else ''
            auth_server = core.split('?')[0]
            uuid, server_port = auth_server.split('@')
            server, port = server_port.split(':')
            params = dict(p.split('=',1) for p in params_part.split('&') if '=' in p)
            outbound = {"type": "vless", "tag": target, "server": server, "server_port": int(port), "uuid": uuid}
            if params.get('security') == 'reality':
                outbound["flow"] = urllib.parse.unquote(params.get('flow','xtls-rprx-vision'))
                outbound["tls"] = {"enabled": True, "server_name": params.get('sni',server),
                    "reality": {"enabled": True, "public_key": urllib.parse.unquote(params.get('pbk','')), "short_id": urllib.parse.unquote(params.get('sid','')).split('#')[0]},
                    "utls": {"enabled": True, "fingerprint": urllib.parse.unquote(params.get('fp','chrome'))}}
            elif params.get('security') == 'tls':
                outbound["tls"] = {"enabled": True, "server_name": urllib.parse.unquote(params.get('sni',server)), "insecure": True}
            if params.get('type') == 'ws':
                outbound["transport"] = {"type": "ws", "path": params.get('path',''), "headers": {"Host": params.get('host','')}}
            cfg = {"log": {"level": "error"},
                "inbounds": [{"type": "mixed", "listen": "127.0.0.1", "listen_port": 10808}],
                "outbounds": [outbound]}
            outfile = f"/opt/data/proxy-skill/node_{target}.json"
            json.dump(cfg, open(outfile,'w'), ensure_ascii=False)
            print(f"OK:{outfile}")
            break
        elif line.startswith('hysteria2://') or line.startswith('hy2://'):
            core = line.split('://')[1]
            params_part = core.split('?')[1] if '?' in core else ''
            auth_server = core.split('?')[0]
            password, server_port = auth_server.split('@')
            server, port = server_port.split(':')
            params = dict(p.split('=',1) for p in params_part.split('&') if '=' in p)
            outbound = {"type": "hysteria2", "tag": target, "server": server, "server_port": int(port),
                "password": password, "tls": {"enabled": True, "server_name": params.get('sni',server), "insecure": True}}
            cfg = {"log": {"level": "error"},
                "inbounds": [{"type": "mixed", "listen": "127.0.0.1", "listen_port": 10808}],
                "outbounds": [outbound]}
            outfile = f"/opt/data/proxy-skill/node_{target}.json"
            json.dump(cfg, open(outfile,'w'), ensure_ascii=False)
            print(f"OK:{outfile}")
            break
PYEOF
)
    if [[ "$CFG_OUT" != OK:* ]]; then continue; fi
    CFG_FILE="${CFG_OUT#OK:}"
    if test_node "$name" "$CFG_FILE" | grep -q OK; then
        echo "✅ 节点 [$name] 可用！切换到它"
        cp "$CFG_FILE" "$SKILL_DIR/reality_active.json"
        sed -i "s|CONFIG=.*|CONFIG=$SKILL_DIR/reality_active.json|" "$SKILL_DIR/proxy.sh"
        bash "$SKILL_DIR/proxy.sh" restart 2>&1 | tail -1
        sed -i "s|LAST_GOOD_NODE=.*|LAST_GOOD_NODE=\"$name\"|" "$SKILL_DIR/subscription.conf"
        echo "✅ 已切换到 $name"
        exit 0
    else
        echo "   ✗ 不可用"
    fi
done < /tmp/auto_switch_candidates.txt

echo "❌ 所有节点均不可用"
exit 1
