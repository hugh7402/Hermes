#!/usr/bin/env bash
# ============================================================
# Batch download from rclone WebDAV remote
# Usage: bash batch-download.sh <remote-name> <source-dir> [file1 file2 ...]
#   or:  bash batch-download.sh pikpak "/Movie/剧名" EP12 EP17 EP21
#
# Features:
#   - Sequential batch download (one file at a time, don't hammer the remote)
#   - rclone's built-in resume (interrupt and rerun — continues from where it left off)
#   - Retry on failure (3 attempts with 5s sleep)
#   - Checksum verification on completion
#   - Progress logging per file
# ============================================================
set -e

RCLONE="${RCLONE:-/tmp/rclone}"
REMOTE="${1}"
SRC_DIR="${2}"
DEST="${3:-/opt/data/PikPak}"
shift 3

if [ -z "$REMOTE" ] || [ -z "$SRC_DIR" ]; then
  echo "用法: bash batch-download.sh <remote-name> <源目录> [下载目录] <file1 file2 ...>"
  echo "示例: bash batch-download.sh pikpak '/Movie/剧名' /opt/data/PikPak/剧名 EP12 EP17 EP21"
  exit 1
fi

mkdir -p "$DEST"

for item in "$@"; do
  # 尝试找文件（支持精确文件名或通配）
  # 如果是 EP12 这种缩写，拼接完整文件名
  FILE="$item"
  if [[ "$FILE" != *.* ]]; then
    # 没有后缀，可能是缩写——先看看远程上有哪些匹配的文件
    echo "  🔍 搜索 $SRC_DIR 中匹配 '$FILE' 的文件..."
    MATCH=$(${RCLONE} lsf "${REMOTE}:${SRC_DIR}" 2>/dev/null | grep -i "$FILE" | head -1)
    if [ -n "$MATCH" ]; then
      FILE="$MATCH"
      echo "  ✅ 匹配到: $FILE"
    else
      echo "  ❌ 未找到匹配 '$FILE' 的文件，跳过"
      continue
    fi
  fi

  SRC="${SRC_DIR}/${FILE}"
  echo ""
  echo "===== [$(date '+%H:%M:%S')] 开始下载: $FILE ====="

  # rclone 自带断点续传，中断后重跑会自动续传
  ${RCLONE} copy "${REMOTE}:${SRC}" "$DEST" \
    --progress \
    --verbose \
    --retries 3 \
    --retries-sleep 5s \
    --checksum \
    2>&1 | tail -20

  if [ $? -eq 0 ]; then
    echo "✅ [$(date '+%H:%M:%S')] 完成: $DEST/$FILE"
  else
    echo "⚠️  首次失败，3 秒后重试..."
    sleep 3
    ${RCLONE} copy "${REMOTE}:${SRC}" "$DEST" \
      --progress \
      --retries 3 \
      --retries-sleep 5s \
      --checksum \
      2>&1 | tail -10
    if [ $? -eq 0 ]; then
      echo "✅ [$(date '+%H:%M:%S')] 重试成功: $DEST/$FILE"
    else
      echo "❌ [$(date '+%H:%M:%S')] 下载失败: $FILE（已跳过）"
    fi
  fi
done

echo ""
echo "===== [$(date '+%H:%M:%S')] 全部任务完成 ====="
echo "📂 目标目录: $DEST"
ls -lh "$DEST" 2>/dev/null | head -30
