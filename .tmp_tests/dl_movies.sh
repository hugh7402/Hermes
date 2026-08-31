#!/bin/bash
# 5 部电影 WebDAV 15 并发下载
mkdir -p /tmp/movie_dl
cd /tmp
# 从 PikPak Movie/ 获取 5 个电影文件名
timeout 60 /tmp/rclone lsf pikpak:/Movie 2>/dev/null | grep -E '心灵捕手|3 Idiots|choristes|Children.of.Heaven|Dangal' > /tmp/movie_list.txt
echo "=== 待下载 ==="
cat /tmp/movie_list.txt
echo "=== 开始 15 并发下载 ==="
timeout 14400 /tmp/rclone copy --files-from /tmp/movie_list.txt pikpak:/Movie /tmp/movie_dl \
  --transfers 15 --buffer-size=32M --multi-thread-streams=0 --timeout 60s --contimeout 30s 2>&1
echo "MOVIE_DL_DONE"
ls -la /tmp/movie_dl/
