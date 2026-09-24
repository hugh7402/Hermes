#!/bin/bash
# auto-git-backup: 自动备份 /opt/data 到 GitHub
# 用法: bash ~/.hermes/scripts/git_backup.sh
# 无变更时静默退出（stdout 为空，cron 不投递）
set -u

# 确保代理运行
bash /opt/data/proxy-skill/proxy.sh start 2>/dev/null
sleep 2

cd /opt/data || exit 1

# 无变更 → 静默退出
if [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

git add -A
git commit -m "auto backup $(date +%Y-%m-%d)" || exit 0
git push 2>&1
exit $?
