#!/bin/bash
# ============================================================================
# 演示启动脚本模板（Mac 双击运行）—— 用于「把单文件 HTML 原型当真实系统演示」
# 目的：① 隐藏地址栏/标签页/书签栏 ② 不带出用户自己的书签与扩展 ③ 用中性 URL 而非 file:// 路径
# 用法：改 FILE 与 PROFILE 两处，和 HTML 放在同一文件夹，chmod +x 后双击
# 结束：关掉系统窗口后，回终端窗口按 ⌃C（trap 会停掉本地服务）
# ============================================================================

cd "$(dirname "$0")" || exit 1
FILE="@@HTML_FILENAME@@"          # ← 改成演示版 HTML 的文件名（不带版本号）
PORT=8080
PROFILE="$HOME/.@@PROFILE_SUFFIX@@"   # ← 独立配置目录，避免带出日常浏览器书签/历史/扩展

if [ ! -f "$FILE" ]; then
  echo "❌ 没找到 $FILE —— 请把本脚本和 HTML 放在同一个文件夹里。"
  read -r -p "按回车键关闭窗口…" _
  exit 1
fi

URL=""
SRV=""
if command -v python3 >/dev/null 2>&1; then
  # 端口被占就 +1（不报错、不要求用户处理）
  while lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do PORT=$((PORT + 1)); done
  # ⚠️ 只监听 127.0.0.1：保密件不上公网、不对外暴露
  python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null' EXIT INT TERM
  ENC=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$FILE")
  URL="http://127.0.0.1:$PORT/$ENC"
  sleep 1
  echo "✅ 本地服务已启动：$URL"
else
  URL="file://$(pwd)/$FILE"     # 回退：没有 python3 就用 file://（应用模式同样隐藏地址栏）
  echo "ℹ️ 没找到 python3，改用本地文件方式打开"
fi

# ⚠️ 用可执行路径而不是 `open -na`：能明确判断「装了没有」，才能走回退分支
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ -x "$CHROME" ]; then
  "$CHROME" --app="$URL" \
            --user-data-dir="$PROFILE" \
            --no-first-run --no-default-browser-check >/dev/null 2>&1 &
  echo "✅ 已用 Chrome 应用模式打开（无地址栏 / 无标签页 / 独立干净配置）"
  echo
  echo "   · 想全屏无边框：把上面那行的 --app= 换成 --kiosk=   （⌘Q 退出）"
  echo "   · 演示结束：先关闭系统窗口，再回到这里按 ⌃C 停止服务"
else
  echo "⚠️ 没找到 Google Chrome，改用默认浏览器（会显示地址栏与标签页）"
  open "$URL"
fi

wait

# ── 交付时另外要做的事 ──────────────────────────────────────────────────
# 1. 演示版 HTML 要从交付版派生，只做三处：页脚版本号置空、Ctrl+D 调试开关禁用、APP.VERSION 中性化
# 2. 同时给一份 `演示前检查清单.md`：Gatekeeper（右键→打开 / xattr -cr）、⌘⇧B 隐藏书签栏、
#    输入法切英文、关通知、缩放 ⌘0、别按 Ctrl+D、别开 DevTools
# 3. ⚠️ 这个脚本是 macOS 专用的；若自己不在 mac 上，只能 bash -n 语法校验 + 验证产物本身，
#    必须在交付说明里讲清「没在目标平台真跑过」，并请用户把终端输出回传
