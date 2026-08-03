#!/bin/bash
# 单文件下载包装：$1=name $2=fname $3=url
export LD_LIBRARY_PATH=/opt/data
name="$1"; fname="$2"; url="$3"
rm -f "/tmp/dl/$fname" "/tmp/dl/$fname.aria2"
echo "[$(date '+%H:%M:%S')] 启动: $name"
/opt/data/aria2c --max-connection-per-server=8 --split=8 --min-split-size=8M \
  --continue=true --max-tries=8 --retry-wait=10 --timeout=120 \
  --console-log-level=warn --dir=/tmp/dl --out="$fname" "$url" > "/tmp/dl_$name.log" 2>&1
echo "[$(date '+%H:%M:%S')] 完成: $name (exit=$?)"
