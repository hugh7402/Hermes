#!/bin/bash
# 心灵猎人 S1 磁力熊版下载: /tmp/xllr_mh_urls.json → aria2 → Movie/心灵猎人第一季/
set -u
export LD_LIBRARY_PATH=/opt/data
DL_DIR=/tmp/xllr_mh_dl
MOVIE_DIR="/opt/data/Movie/心灵猎人第一季(2017)"
mkdir -p "$DL_DIR" "$MOVIE_DIR"

python3 - << 'PYEOF' > /tmp/xllr_mh_jobs.txt
import json
urls = json.load(open('/tmp/xllr_mh_urls.json'))
for name, url in urls.items():
    print(f'{name}|{url}')
PYEOF

total=$(wc -l < /tmp/xllr_mh_jobs.txt)
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
        if [ -n "$dur" ] && [ "$(python3 -c "print('1' if float('$dur') > 100 else '0')" 2>/dev/null)" = "1" ]; then
            cp "$DL_DIR/$name" "$MOVIE_DIR/$name" && rm -f "$DL_DIR/$name"
            echo "  ✅ $name 完成入库 (${dur%.*}s)"
        else
            echo "  ❌ $name 校验失败 (dur=$dur)"
            rm -f "$DL_DIR/$name"
        fi
    ) &
done < /tmp/xllr_mh_jobs.txt

wait
echo "=== 心灵猎人下载完成 ==="
ls "$MOVIE_DIR" | wc -l
