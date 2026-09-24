#!/bin/bash
# Hindsight daemon 启动脚本（2026-08-17 修复后固化）
# 关键：HOME 必须是 /opt/data（否则 pg0 会在 /opt/data/home/.pg0 分裂数据）
#       DATABASE_URL 必须指定 hindsight-embed-hermes 实例（否则连空实例）
set -e

export HOME=/opt/data
export HINDSIGHT_API_DATABASE_URL=pg0://hindsight-embed-hermes
set -a
source /opt/data/.hindsight/profiles/hermes.env
set +a
export HINDSIGHT_API_DATABASE_URL=pg0://hindsight-embed-hermes

# 清掉可能残留的代理变量（socksio 未装会导致 LiteLLM 初始化失败）
unset https_proxy http_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY 2>/dev/null || true

BIN=/opt/data/.cache/uv/archive-v0/UvuKov5JptV1YgV0DscNQ/bin/hindsight-api
if [ ! -x "$BIN" ]; then
  BIN=$(command -v hindsight-api || echo "")
  [ -n "$BIN" ] || { echo "hindsight-api binary not found"; exit 1; }
fi

# 已运行则跳过
if pgrep -f "hindsight_api.main --idle-timeout" >/dev/null 2>&1; then
  echo "hindsight daemon already running"
  exit 0
fi

setsid nohup "$BIN" --idle-timeout 300 --port 9177 >> /opt/data/.hindsight/profiles/hermes.log 2>&1 &
echo "launched daemon pid $!"
sleep 20
curl -s --max-time 4 http://127.0.0.1:9177/health && echo " <- healthy" || echo "health check failed (still booting?)"
