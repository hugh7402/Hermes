#!/bin/bash
# 启动脚本（macOS）：起本地服务（只监听回环地址）→ 普通窗口打开浏览器（地址栏可见）
# 结束使用：关闭浏览器窗口后，回到本终端按 ⌃C（服务一并停止）
# 用法：与 index.html、serve.py 同目录；保存为“启动.command”并 chmod +x

cd "$(dirname "$0")" || exit 1
echo
PORT=8080
PROFILE="$HOME/.drs-chrome"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -f index.html ]; then
  echo "❌ 同目录下没有 index.html —— 请把本脚本与 index.html、serve.py 放在一起。"
  read -r -p "按回车键关闭窗口…" _
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  while lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do PORT=$((PORT + 1)); done
  python3 serve.py "$PORT" >/dev/null 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null' EXIT INT TERM
  URL="http://localhost:$PORT/"
  sleep 1
  echo "✅ 服务已启动：$URL"
else
  echo "⚠️ 未找到 python3，改用本地文件方式打开（地址栏会显示文件路径，且页面路由不可用）"
  URL="file://$(pwd)/index.html"
fi

if [ -x "$CHROME" ]; then
  "$CHROME" --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check \
            --new-window "$URL" >/dev/null 2>&1 &
  echo "✅ 已打开浏览器窗口，地址栏为：$URL"
  echo
  echo "   · 系统内切换页面时，地址栏会变为对应页面地址（例如 /xzzwsjml、/sjqxjgmx）"
  echo "   · 若想隐藏地址栏与标签页：把上面 --new-window 换成 --app=（全屏用 --kiosk=）"
  echo "   · 结束使用：先关闭浏览器窗口，再回到这里按 ⌃C 停止服务"
else
  echo "⚠️ 未找到 Google Chrome，改用默认浏览器打开：$URL"
  open "$URL"
fi

wait
