#!/bin/bash
# 重新取4部电影CDN URL并下载，并发限制3
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
# 收集所有 URL 到一个临时文件给 aria2 多 URL 方式
urls_file=/tmp/dl_urls_$$.txt
: > "$urls_file"
declare -A FNAME=()
idx=0
while IFS='|' read -r name fname url; do
  [ -z "$url" ] && { echo "SKIP $name (无URL)"; continue; }
  idx=$((idx+1))
  rm -f "/tmp/dl/$fname" "/tmp/dl/$fname.aria2"
  echo "$url" >> "$urls_file"
  FNAME[$idx]="$fname"
  echo "  [$idx] $name -> $fname"
done < <(grep -v '^$' /tmp/movie_urls.txt)

# aria2 多URL：每个URL独立 -x 参数，用 --max-concurrent-downloads=3
args=()
while IFS= read -r u; do
  [ -n "$u" ] && args+=("$u")
done < "$urls_file"

/opt/data/aria2c --max-concurrent-downloads=3 --max-connection-per-server=8 --split=8 --min-split-size=8M \
  --continue=true --max-tries=8 --retry-wait=10 --timeout=120 \
  --console-log-level=notice --dir=/tmp/dl "${args[@]}" > /tmp/dl_movies_batch.log 2>&1

echo "[$(date '+%H:%M:%S')] aria2退出: $?"
rm -f "$urls_file"
