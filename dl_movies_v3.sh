#!/bin/bash
# 取4部电影URL，并发3下载（用计数控制）
export LD_LIBRARY_PATH=/opt/data
cd /opt/data

echo "[$(date '+%H:%M:%S')] 重新取URL..."
timeout 90 /opt/data/.venv/bin/python3 << 'PYEOF'
import json, asyncio
from pikpakapi import PikPakApi
async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']
    r = await client.path_to_id('/Inbox-JAV')
    files = await client.file_list(parent_id=r[0]['id'])
    targets = {}
    for f in files.get('files', []):
        n = f.get('name','')
        if f.get('kind') == 'drive#folder':
            if any(k in n for k in ['Master','Claude','olombiana']):
                inner = await client.file_list(parent_id=f['id'])
                for fi in inner.get('files', []):
                    if fi.get('kind') == 'drive#file' and fi.get('size',0) > 100000000:
                        fn = fi['name']
                        if 'Master' in fn: targets['请做我的主人'] = (fn, fi['id'])
                        elif 'Claude' in fn: targets['应召女王'] = (fn, fi['id'])
                        elif 'olombiana' in fn: targets['致命黑兰'] = (fn, fi['id'])
        elif 'Swimming' in n:
            targets['池畔谋杀案'] = (n, f['id'])
    out = []
    for name, (fn, fid) in targets.items():
        info = await client.get_download_url(fid)
        url = info.get('web_content_link') or ''
        out.append(f'{name}|{fn}|{url}')
        print(f'{name}: URL={len(url)}chars')
    open('/tmp/movie_urls.txt','w').write('\n'.join(out))
asyncio.run(run())
PYEOF

echo "[$(date '+%H:%M:%S')] 启动下载(并发3)..."
running=0
while IFS='|' read -r name fname url; do
  [ -z "$url" ] && { echo "SKIP $name (无URL)"; continue; }
  # 等待并发槽
  while [ "$running" -ge 3 ]; do
    sleep 5
    running=$(pgrep -fc "aria2c.*--out" 2>/dev/null || echo 0)
  done
  rm -f "/tmp/dl/$fname" "/tmp/dl/$fname.aria2"
  echo "[$(date '+%H:%M:%S')] 启动: $name"
  /opt/data/aria2c --max-connection-per-server=8 --split=8 --min-split-size=8M \
    --continue=true --max-tries=8 --retry-wait=10 --timeout=120 \
    --console-log-level=warn --dir=/tmp/dl --out="$fname" "$url" > "/tmp/dl_$name.log" 2>&1 &
  running=$(pgrep -fc "aria2c.*--out" 2>/dev/null || echo 0)
done < <(grep -v '^$' /tmp/movie_urls.txt)

echo "[$(date '+%H:%M:%S')] 等待剩余完成..."
wait
echo "[$(date '+%H:%M:%S')] 全部完成"
