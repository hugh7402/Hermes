#!/bin/bash
# 护宝寻踪 36 集批量下载: /tmp/hbxz_urls.json → aria2 → /tmp/hbxz_dl/
# 并发 3 个，下载完 ffprobe 校验，通过则 cp 到 /opt/data/Movie/
set -u
export LD_LIBRARY_PATH=/opt/data
DL_DIR=/tmp/hbxz_dl
MOVIE_DIR=/opt/data/Movie
mkdir -p "$DL_DIR"

python3 - "$DL_DIR" << 'PYEOF' > /tmp/hbxz_jobs.txt
import json, sys, re
dl = sys.argv[1]
urls = json.load(open('/tmp/hbxz_urls.json'))
jobs = []
for name, url in sorted(urls.items(), key=lambda x: int(re.search(r'(\d+)', x[0]).group(1))):
    out = name
    jobs.append(f'{out}|{url}')
print('\n'.join(jobs))
PYEOF

# 逐批下载（并发 3）
total=$(wc -l < /tmp/hbxz_jobs.txt)
echo "共 $total 集"
done=0
while IFS='|' read -r name url; do
    [ -z "$name" ] && continue
    # 等待槽位（最多 3 个 aria2）
    while [ "$(pgrep -fc aria2c)" -ge 3 ]; do
        sleep 10
    done
    # 已完成的跳过
    if [ -f "$MOVIE_DIR/$name" ] && [ -s "$MOVIE_DIR/$name" ]; then
        echo "✅ $name 已入库，跳过"
        done=$((done+1))
        continue
    fi
    echo "▶️ 下载 $name ..."
    (
        rm -f "$DL_DIR/$name"
        /opt/data/aria2c --max-connection-per-server=8 --split=8 --min-split-size=8M \
            --continue=true --max-tries=5 --retry-wait=8 --timeout=120 \
            --console-log-level=error --dir="$DL_DIR" --out="$name" "$url" > /dev/null 2>&1
        # 校验
        dur=$(/usr/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "$DL_DIR/$name" 2>/dev/null)
        if [ -n "$dur" ] && [ "$(python3 -c "print('1' if float('$dur') > 100 else '0')" 2>/dev/null)" = "1" ]; then
            cp "$DL_DIR/$name" "$MOVIE_DIR/$name" && rm -f "$DL_DIR/$name"
            echo "  ✅ $name 完成入库 (${dur%.*}s)"
        else
            echo "  ❌ $name 校验失败 (dur=$dur)"
            rm -f "$DL_DIR/$name"
        fi
    ) &
    done=$((done+1))
done < /tmp/hbxz_jobs.txt

wait
echo "=== 全部完成 ==="
ls "$MOVIE_DIR" | grep 护宝 | wc -l
