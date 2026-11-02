#!/bin/bash
# 用最小环境跑一个脚本，复现 cron 的真实处境。
#
# 用法:
#   run_under_cron_env.sh /opt/data/scripts/xxx.sh [HOME]
#   run_under_cron_env.sh -e 'git -C /opt/data ls-remote --heads origin main'
#
# 为什么需要它：手敲能跑不等于 cron 能跑。cron 的 PATH 很短、HOME 可能不是你的登录 HOME，
# 依赖登录 shell 的 PATH、全局 git 配置、全局凭据的脚本会在这里现原形。
set -u

MIN_PATH="/usr/bin:/bin:/usr/local/bin"
CRON_HOME="${2:-/opt/data}"

export PATH="$MIN_PATH"
export HOME="$CRON_HOME"

if [ "${1:-}" = "-e" ]; then
  shift
  echo "-- 最小环境命令: $*" >&2
  exec /bin/bash -c "$*"
fi

if [ -z "${1:-}" ] || [ ! -f "$1" ]; then
  echo "用法: $0 <脚本路径> [HOME]   或   $0 -e '<命令>'" >&2
  exit 2
fi

SCRIPT="$1"
echo "-- 最小环境运行: $SCRIPT" >&2
echo "   PATH=$PATH" >&2
echo "   HOME=$HOME" >&2
"/bin/bash" "$SCRIPT"
RC=$?
echo "-- 退出码: $RC" >&2

if [ "$RC" -eq 127 ]; then
  echo "   127 = 命令找不到。几乎总是 PATH/HOME 差异，不是真的没装：" >&2
  echo "   把解释器/工具换成绝对路径（如 /opt/data/.venv/bin/python3），别依赖 uv/pyenv/nvm。" >&2
fi

exit "$RC"
