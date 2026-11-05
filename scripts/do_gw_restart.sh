#!/bin/bash
# gateway 重启（延迟 12 秒，先让上一条回复发出去再动手）
# 2026-11-03 修正：s6-svc 不在默认 PATH 里（在 /command/s6-svc），
# 上一版用裸命令名导致 exit 127，重启静默失败。
sleep 12
{
  echo ""
  echo "=== 重启开始 $(date '+%F %T') ==="
  S6=/command/s6-svc
  [ -x "$S6" ] || S6=$(command -v s6-svc)
  if [ -z "$S6" ]; then
    echo "❌ 找不到 s6-svc，回退到 hermes gateway restart"
    /opt/hermes/bin/hermes gateway restart
  else
    "$S6" -r /run/service/gateway-default
    echo "s6-svc -r 退出码 $?"
  fi
} >> /opt/data/.gateway_restart.log 2>&1
