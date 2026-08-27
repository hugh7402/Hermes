#!/bin/bash
# 补下 JUR-837.mp4（主批次列表遗漏）
mkdir -p /tmp/dl2
timeout 5400 /tmp/rclone copy "pikpak:/Inbox-JAV/JUR-837.mp4" /tmp/dl2 \
  --transfers 15 --buffer-size=32M --multi-thread-streams=0 --timeout 60s --contimeout 30s 2>&1
echo "JUR837_DONE"
