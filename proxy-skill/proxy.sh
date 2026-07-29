#!/usr/bin/env bash
# sing-box 代理服务管理脚本
# 配置: /opt/data/proxy-skill/reality_us01.json (REALITY 美国圣何塞01)
# 端口: 10808 (SOCKS5/HTTP mixed)
set -e

SB=/opt/data/proxy-skill/sing-box
CONFIG=/opt/data/proxy-skill/reality_us01.json
PIDFILE=/opt/data/proxy-skill/sing-box.pid
LOGFILE=/opt/data/proxy-skill/sing-box.log

case "$1" in
  start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
      echo "已在运行 (PID $(cat $PIDFILE))"
      exit 0
    fi
    $SB check -c "$CONFIG" 2>&1 || { echo "配置校验失败"; exit 1; }
    nohup "$SB" run -c "$CONFIG" > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 2
    if kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
      echo "启动成功 (PID $(cat $PIDFILE))"
      # 验证连通性
      if curl -s --max-time 10 -x socks5://127.0.0.1:10808 https://ifconfig.me >/dev/null 2>&1; then
        echo "代理可用，出口: $(curl -s --max-time 5 -x socks5://127.0.0.1:10808 https://ifconfig.me 2>/dev/null)"
      else
        echo "⚠️ 代理启动但连通性测试失败，查看日志: $LOGFILE"
      fi
    else
      echo "启动失败，查看日志: $LOGFILE"
      tail -5 "$LOGFILE"
      rm -f "$PIDFILE"
      exit 1
    fi
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      PID=$(cat "$PIDFILE")
      kill "$PID" 2>/dev/null && echo "已停止 (PID $PID)"
      rm -f "$PIDFILE"
    else
      echo "未运行"
    fi
    ;;
  restart)
    $0 stop 2>/dev/null || true
    sleep 1
    $0 start
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
      echo "运行中 (PID $(cat $PIDFILE))"
      echo "出口 IP: $(curl -s --max-time 5 -x socks5://127.0.0.1:10808 https://ifconfig.me 2>/dev/null || echo '测试失败')"
    else
      echo "未运行"
      exit 1
    fi
    ;;
  log)
    tail -30 "$LOGFILE"
    ;;
  test)
    echo "=== 出口 IP ==="
    curl -s --max-time 10 -x socks5://127.0.0.1:10808 https://ifconfig.me
    echo ""
    echo "=== Google ==="
    curl -s --max-time 10 -x socks5://127.0.0.1:10808 -o /dev/null -w "HTTP %{http_code} time=%{time_total}s\n" https://www.google.com
    echo "=== javdb ==="
    curl -s --max-time 15 -x socks5://127.0.0.1:10808 -o /dev/null -w "HTTP %{http_code} time=%{time_total}s\n" https://javdb.com
    ;;
  *)
    echo "用法: $0 {start|stop|restart|status|log|test}"
    exit 1
    ;;
esac
