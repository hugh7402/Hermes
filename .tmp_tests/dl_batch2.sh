#!/bin/bash
# 并发下载已就绪的 7 个文件（WebDAV --transfers 4，低内存）
mkdir -p /tmp/dl2
cat > /tmp/dl2_list.txt << 'EOF'
GARA-025.mp4
CAWB-025.mp4
IPZZ-914.mp4
JUR-794.mp4
DLDSS-525.mp4
IPZZ-879-C.mp4
DVMM-415-C.mp4
EOF
timeout 10800 /tmp/rclone copy --files-from /tmp/dl2_list.txt pikpak:/Inbox-JAV /tmp/dl2 \
  --transfers 4 --buffer-size=32M --multi-thread-streams=0 --timeout 60s --contimeout 30s 2>&1
echo "ALL_DONE"
