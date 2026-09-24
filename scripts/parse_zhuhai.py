"""解析 zhuhaiuk 免费订阅，提取 US/TW/HK/KR 节点完整链接"""
import base64, re, json, urllib.parse

raw = open('/tmp/zhuhai_nodes.txt','rb').read()
try:
    txt = base64.b64decode(raw).decode()
except Exception:
    txt = raw.decode(errors='ignore')
lines = [l for l in txt.splitlines() if l.strip()]

targets = []
for l in lines:
    # 节点名在 # 后面（可能是明文或 URL 编码）
    name_match = re.search(r'#([^#]*)$', l)
    name = ''
    if name_match:
        try:
            name = urllib.parse.unquote(name_match.group(1))
        except Exception:
            name = name_match.group(1)
    if any(reg in name for reg in ['US', 'TW', 'HK', 'KR', 'JP']):
        targets.append({'name': name, 'url': l})

print(f'目标节点: {len(targets)}')
for t in targets:
    print(f"{t['name']}\n  {t['url'][:220]}\n")
json.dump(targets, open('/tmp/zhuhai_targets.json','w'), ensure_ascii=False, indent=1)
