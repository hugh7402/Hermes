#!/bin/bash
# 低内存模式：从 PikPak WebDAV 拉取 HMN-896 + IPZZ-925
# 背景：系统内存仅剩 ~1.6G，之前用大 buffer rclone 直接挤爆内存死机
# 对策：--buffer-size=32M --transfers=1 串行下载，内存占用 <100MB
DEST=/tmp/dl
INBOX=/opt/data/PikPak/Inbox-JAV
FILES=(
  "HMN-896-愛花未滿-多P轮奸中出 被高薪职位诱骗被下药后被轮奸中出的极品尤物.mp4"
  "IPZZ-925-瀬緒凛-多P轮奸中出 被社长强奸调教并被轮奸中出的极品尤物前台小姐.mp4"
)
FAIL=0
for f in "${FILES[@]}"; do
  echo "=== [$(date +%H:%M:%S)] 下载: $f ==="
  timeout 5400 /tmp/rclone copy "pikpak:/Inbox-JAV/$f" "$DEST" \
    --buffer-size=32M --multi-thread-streams=0 --timeout 60s --contimeout 30s --retries 3 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "[$(date +%H:%M:%S)] 下载失败 rc=$rc: $f"
    FAIL=1
    continue
  fi
  # ffprobe 校验
  dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$DEST/$f" 2>/dev/null)
  size=$(stat -c%s "$DEST/$f" 2>/dev/null)
  echo "[$(date +%H:%M:%S)] 校验: duration=$dur size=$size"
  if [ -z "$dur" ] || [ "$dur" = "N/A" ]; then
    echo "[$(date +%H:%M:%S)] 校验失败(损坏): $f"
    FAIL=1
    continue
  fi
  mv "$DEST/$f" "$INBOX/$f"
  echo "[$(date +%H:%M:%S)] 已搬入: $INBOX/$f"
done
echo "ALL_DONE FAIL=$FAIL"
