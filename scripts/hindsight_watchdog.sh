#!/bin/bash
# Hindsight 看门狗（cron 每 10 分钟跑一次）
#
# 设计：健康时 stdout 完全为空 → cron 不投递任何消息；只有"掉线并已拉起"或"拉起失败"才输出。
# 背景：keepalive hook 需要重启 gateway 才生效，本脚本是不依赖 gateway 的独立兜底。
set -u

HEALTH_URL="http://127.0.0.1:9177/health"
LOG=/opt/data/.hindsight/watchdog.log
mkdir -p "$(dirname "$LOG")" 2>/dev/null

probe() {
  curl -s -m 5 --noproxy '*' "$HEALTH_URL" 2>/dev/null | grep -q '"status":"healthy"'
}

# 1) 健康 → 静默退出
if probe; then
  exit 0
fi

# 2) 掉线 → 记录并拉起
echo "[$(date '+%F %T')] unhealthy, launching" >> "$LOG"
bash /opt/data/scripts/hindsight_start.sh >> "$LOG" 2>&1

# 3) 最多等 90 秒（冷启动要一分多钟）
for i in $(seq 1 18); do
  sleep 5
  if probe; then
    echo "✅ Hindsight 掉线后已自动拉起（$(date '+%m-%d %H:%M')）"
    echo "[$(date '+%F %T')] recovered after $((i*5))s" >> "$LOG"
    exit 0
  fi
done

echo "⚠️ Hindsight 掉线且自动拉起失败，需人工介入（$(date '+%m-%d %H:%M')）。日志：$LOG"
echo "[$(date '+%F %T')] recovery FAILED" >> "$LOG"
exit 1
