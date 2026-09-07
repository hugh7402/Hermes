#!/bin/bash
# 轮询 WebDAV 直到看到知无涯者文件，然后下载
FILE="知无涯者.The.Man.Who.Knew.Infinity.2015.1080p.WEB-DL.AAC.H264-ParkHD.mp4"
mkdir -p /tmp/movie_dl
echo "$FILE" > /tmp/zwnz_list.txt
for i in $(seq 1 30); do
  if timeout 50 /tmp/rclone lsf --dir-cache-time 0s "pikpak:/Movie" 2>/dev/null | grep -q "ParkHD"; then
    echo "✅ WebDAV 已可见 (第 ${i} 次探测)"
    timeout 1800 /tmp/rclone copy --files-from /tmp/zwnz_list.txt "pikpak:/Movie" /tmp/movie_dl \
      --transfers 15 --buffer-size=32M --multi-thread-streams=0 --timeout 60s --contimeout 30s 2>&1
    echo "ZWNZ_DL_DONE"
    exit 0
  fi
  echo "[$i] WebDAV 暂不可见，等待..."
  sleep 60
done
echo "TIMEOUT_30MIN_NOT_VISIBLE"
