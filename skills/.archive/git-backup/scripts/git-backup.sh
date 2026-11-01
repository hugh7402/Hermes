#!/bin/bash
# Hermes Git 自动备份脚本
# 用于 cron 定时推送，无输出 = 无变更，有变更时自动 commit + push

set -e
REPO_DIR="/opt/data"

cd "$REPO_DIR"

# 检查是否有变更
git add -A

# 无变更则安静退出
if git diff --cached --quiet; then
    exit 0
fi

# 有变更则提交并推送
git commit -m "Auto backup $(date '+%Y-%m-%d %H:%M')"
git push origin main 2>&1 || echo "[WARN] git push failed - check auth"
