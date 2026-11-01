#!/usr/bin/env bash
# aria2 下载 PikPak CDN 文件
# 用法: ./pikpak_dl_aria2.sh [文件名1 文件名2 ...]
# 默认下载 /tmp/pikpak_urls.json 中的所有文件
set -euo pipefail

export LD_LIBRARY_PATH=/opt/data
ARIA2C=/opt/data/aria2c
LOCAL=/opt/data/PikPak/Inbox-JAV
mkdir -p "$LOCAL"

URLS_JSON=/tmp/pikpak_urls.json
if [ ! -f "$URLS_JSON" ]; then
    echo "❌ 无直链文件: $URLS_JSON"
    echo "先用 JAV 智能体获取直链"
    exit 1
fi

# 生成 aria2 输入文件
INPUT_FILE=$(mktemp /tmp/aria2_input.XXXXXX)

# 🚨 先杀掉旧下载进程，避免冲突覆盖文件
pkill -f pikpak_cdn_dl.py 2>/dev/null || true
pkill -f "rclone.*copy.*Inbox-JAV" 2>/dev/null || true
# 清理残留 aria2 控制文件
rm -f "$LOCAL"/*.aria2 2>/dev/null || true

if [ $# -gt 0 ]; then
    for fn in "$@"; do
        url=$(python3 -c "import json; d=json.load(open('$URLS_JSON')); print(d['$fn'])" 2>/dev/null) || {
            echo "⚠️ 跳过 $fn：无直链"
            continue
        }
        echo "$url" >> "$INPUT_FILE"
        echo "  out=$fn" >> "$INPUT_FILE"
    done
else
    python3 -c "
import json
d = json.load(open('$URLS_JSON'))
with open('$INPUT_FILE', 'w') as f:
    for name, url in d.items():
        f.write(url + '\n')
        f.write(f'  out={name}\n')
"
fi

if [ ! -s "$INPUT_FILE" ]; then
    echo "❌ 没有要下载的文件"
    rm -f "$INPUT_FILE"
    exit 1
fi

echo "📥 开始 aria2 下载 ($(wc -l < "$INPUT_FILE") URL)..."
$ARIA2C \
    --max-connection-per-server=8 \
    --split=8 \
    --min-split-size=8M \
    --continue=true \
    --auto-file-renaming=false \
    --max-tries=5 \
    --retry-wait=5 \
    --timeout=120 \
    --connect-timeout=30 \
    --console-log-level=notice \
    --dir="$LOCAL" \
    --input-file="$INPUT_FILE"

rm -f "$INPUT_FILE"
echo "✅ 下载完成"
ls -lh "$LOCAL"/*.mp4 2>/dev/null
