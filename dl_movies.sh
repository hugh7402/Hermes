#!/bin/bash
# 下载4部电影（从 /tmp/movie_urls.txt 读取 URL）
export LD_LIBRARY_PATH=/opt/data
cd /opt/data

pids=()
while IFS='|' read -r name fname url; do
  [ -z "$url" ] && continue
  rm -f "/tmp/dl/$fname" "/tmp/dl/$fname.aria2"
  echo "=== 启动: $name ($fname) ==="
  /opt/data/aria2c --max-connection-per-server=8 --split=8 --min-split-size=8M \
    --continue=true --max-tries=5 --retry-wait=5 --timeout=120 \
    --console-log-level=warn --dir=/tmp/dl --out="$fname" "$url" > "/tmp/dl_$name.log" 2>&1 &
  pids+=($!)
  echo "  PID=$!"
done < <(grep -v '^$' /tmp/movie_urls.txt)

echo "等待 ${#pids[@]} 个下载..."
wait
echo "全部完成"
