#!/bin/bash
# 处理离线文件夹 + 15 并发下载（用户确认：15 并发才能到 24M/s）
cd /opt/data/.tmp_tests
export PATH=/opt/data/.venv/bin:$PATH
echo "===== [1/2] 处理离线文件夹 ====="
python3 fix_folders.py 2>&1
echo "===== [2/2] 15 并发下载 ====="
mkdir -p /tmp/dl2
timeout 14400 /tmp/rclone copy --files-from /tmp/dl2_list.txt pikpak:/Inbox-JAV /tmp/dl2 \
  --transfers 15 --buffer-size=32M --multi-thread-streams=0 --timeout 60s --contimeout 30s 2>&1
echo "ALL_DONE"
