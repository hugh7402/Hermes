#!/bin/bash
# 心灵猎人 批量下载: /tmp/xllr_urls.json → aria2 → /tmp/xllr_dl/ → Movie/
set -u
export LD_LIBRARY_PATH=/opt/data
DL_DIR=/tmp/xllr_dl
MOVIE_DIR=/opt/data/Movie
mkdir -p "$DL_DIR"

python3 - "$DL_DIR" << 'PYEOF' > /tmp/xllr_jobs.txt
import json, sys
dl = sys.argv[1]
urls = json.load(open('/tmp/xllr_urls.json'))
jobs = []
for name, url in urls.items():
    jobs.append(f'{name}|{url}')
print('\n'.join(jobs))
PYEOF

total=$(wc -l < /tmp/xllr_jobs.txt)
echo "共 $total 集待下载"
while IFS='|' read -r name url; do
    [ -z "$name" ] && continue
    while [ "$(pgrep -fc aria2c)" -ge 3 ]; do
        sleep 10
    done
    if [ -f "$MOVIE_DIR/$name" ] && [ -s "$MOVIE_DIR/$name" ]; then
        echo "✅ $name 已入库，跳过"
        continue
    fi
    echo "▶️ 下载 $name ..."
    (
        rm -f "$DL_DIR/$name"
        /opt/data/aria2c --max-connection-per-server=8 --split=8 --min-split-size=8M \
            --continue=true --max-tries=5 --retry-wait=8 --timeout=120 \
            --console-log-level=error --dir="$DL_DIR" --out="$name" "$url" > /dev/null 2>&1
        dur=$(/usr/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "$DL_DIR/$name" 2>/dev/null)
        if [ -n "$dur" ] && [ "$(echo "$dur > 100" | bc 2>/dev/null)" = "1" ]; then
            cp "$DL_DIR/$name" "$MOVIE_DIR/$name" && rm -f "$DL_DIR/$name"
            echo "  ✅ $name 完成入库 (${dur%.*}s)"
        else
            echo "  ❌ $name 校验失败 (dur=$dur)"
            rm -f "$DL_DIR/$name"
        fi
    ) &
done < /tmp/xllr_jobs.txt

wait
echo "=== 心灵猎人下载完成 ==="
ls "$MOVIE_DIR" | grep 心灵猎人 | wc -l
