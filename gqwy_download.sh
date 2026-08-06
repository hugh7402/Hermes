#!/bin/bash
# 怪奇物语 S1 批量下载: /tmp/gqwy_urls.json → aria2 → /tmp/gqwy_dl/ → Movie/怪奇物语第一季/
set -u
export LD_LIBRARY_PATH=/opt/data
DL_DIR=/tmp/gqwy_dl
MOVIE_DIR="/opt/data/Movie/怪奇物语第一季(2016)"
mkdir -p "$DL_DIR" "$MOVIE_DIR"

python3 - << 'PYEOF' > /tmp/gqwy_jobs.txt
import json, re
urls = json.load(open('/tmp/gqwy_urls.json'))
# 按集数排序，字幕文件排视频后面
def key(name):
    m = re.search(r'E(\d+)', name)
    ep = int(m.group(1)) if m else 99
    return (ep, 1 if name.endswith('.mkv') else 0)
for name, url in sorted(urls.items(), key=lambda x: key(x[0])):
    print(f'{name}|{url}')
PYEOF

total=$(wc -l < /tmp/gqwy_jobs.txt)
echo "共 $total 个文件待下载"
while IFS='|' read -r name url; do
    [ -z "$name" ] && continue
    while [ "$(pgrep -fc aria2c)" -ge 3 ]; do
        sleep 10
    done
    if [ -f "$MOVIE_DIR/$name" ] && [ -s "$MOVIE_DIR/$name" ]; then
        echo "✅ $name 已存在，跳过"
        continue
    fi
    echo "▶️ 下载 $name ..."
    (
        rm -f "$DL_DIR/$name"
        /opt/data/aria2c --max-connection-per-server=8 --split=8 --min-split-size=8M \
            --continue=true --max-tries=5 --retry-wait=8 --timeout=120 \
            --console-log-level=error --dir="$DL_DIR" --out="$name" "$url" > /dev/null 2>&1
        if [[ "$name" == *.mkv ]]; then
            dur=$(/usr/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "$DL_DIR/$name" 2>/dev/null)
            if [ -n "$dur" ] && [ "$(python3 -c "print('1' if float('$dur') > 500 else '0')" 2>/dev/null)" = "1" ]; then
                cp "$DL_DIR/$name" "$MOVIE_DIR/$name" && rm -f "$DL_DIR/$name"
                echo "  ✅ $name 完成入库 (${dur%.*}s)"
            else
                echo "  ❌ $name 校验失败 (dur=$dur)"
                rm -f "$DL_DIR/$name"
            fi
        else
            # 字幕文件直接入库
            cp "$DL_DIR/$name" "$MOVIE_DIR/$name" && rm -f "$DL_DIR/$name"
            echo "  ✅ $name 字幕入库"
        fi
    ) &
done < /tmp/gqwy_jobs.txt

wait
echo "=== 怪奇物语下载完成 ==="
ls "$MOVIE_DIR" | wc -l
