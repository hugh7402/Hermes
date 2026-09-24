#!/bin/bash
# 批量下载 11 个番号（WebDAV，每组 2 个并行，避免磁盘/内存压力）
cd /opt/data
R=/opt/data/bin/rclone
D=/opt/data/.dl_tmp/jav
mkdir -p "$D"

# 已映射：云端文件名 → 本地最终名（含 -C 后缀）
declare -a FILES=(
  "START-603-C:489155.com@START-603-C.mp4"
  "MFYD-172-C:489155.com@MFYD-172-C.mp4"  # 已在顶层，无需再映射
)
echo "脚本框架"