#!/bin/bash
# auto-git-backup: 自动备份 /opt/data 到 GitHub
# 无变更时静默退出（stdout 为空，cron 不投递）
#
# 2026-11-01 修复：之前把 chrome/installs/tools 里的浏览器二进制（199MB、257MB）提交进 git，
# 被 GitHub 单文件 100MB 限制拒收，导致 10-12 起连续 6 次推送失败、提交堆积。
# 现在加两道闸：① .gitignore 排除大目录 ② 提交前扫超限文件，超了就拆下来并告警。
set -u

MAX_MB=90           # 单文件上限，GitHub 硬限 100MB，留 10MB 余量
BIG_DIRS="chrome installs tools"

# 确保代理运行（推送需要）
bash /opt/data/proxy-skill/proxy.sh start >/dev/null 2>&1
sleep 2

cd /opt/data || exit 1

# 无变更 → 静默退出
if [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

git add -A

# ── 闸一：超大文件从暂存区拆下来，不让它进提交
BIG=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || continue
  sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
  if [ "$sz" -gt $((MAX_MB * 1048576)) ]; then
    BIG="$BIG$((sz / 1048576))MB  $f"$'\n'
    git restore --staged -- "$f" 2>/dev/null || git rm --cached -q -- "$f" 2>/dev/null
  fi
done < <(git diff --cached --name-only)

if [ -n "$BIG" ]; then
  echo "⚠️ 以下文件超过 ${MAX_MB}MB，已从本次提交中剔除（未删除原文件）："
  printf '%s' "$BIG"
  echo ""
  echo "如果这类目录本就不该进 git，请把它的上级目录加进 /opt/data/.gitignore。"
fi

# ── 闸二：确认大目录没被重新跟踪
for d in $BIG_DIRS; do
  if git ls-files --error-unmatch "$d" >/dev/null 2>&1; then
    echo "⚠️ 目录 $d 仍被 git 跟踪，正在从索引移除（文件保留）"
    git rm -r --cached -q "$d" 2>/dev/null
  fi
done

# ── 没有实际可提交内容就退出
if git diff --cached --quiet; then
  exit 0
fi

git commit -q -m "auto backup $(date +%Y-%m-%d)" || exit 0

# ── 推送（失败时输出原因，cron 会告警）
if ! git push origin HEAD 2>&1; then
  echo "❌ 推送失败。常见原因："
  echo "  - 代理不通：bash /opt/data/proxy-skill/proxy.sh status"
  echo "  - 仍有超大文件：git ls-files -z | xargs -0 ls -la 2>/dev/null | awk '\$5>90000000'"
  echo "  - 远端有新提交：git pull --rebase origin main"
  exit 1
fi

echo "✅ 已备份 $(git rev-parse --short HEAD)"
exit 0
