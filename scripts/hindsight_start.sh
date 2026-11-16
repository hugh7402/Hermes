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

# 🚨 必须清掉 PYTHONPATH / PYTHONHOME
# keepalive 是 gateway 的 hook，会继承 gateway 的环境：
#   PYTHONPATH=/opt/hermes/.:/opt/hermes/.venv/lib/python3.14/site-packages
# 于是跑在 python3.13 上的 hindsight-api 会去 3.14 的 site-packages 里 import pydantic，
# pydantic_core 的 .so 是 cpython-314 编译的 → ImportError: cannot import name 'ArgsKwargs'
# 表现为 daemon 反复启动失败、keepalive 日志刷 'agent:end unhealthy'。
unset PYTHONPATH PYTHONHOME 2>/dev/null || true
export PYTHONNOUSERSITE=1

# 🚨 PG 标准目录必须存在，且 pg_tblspc 里绝对不能放普通文件
#   - disk-cleanup 插件会把空目录当垃圾删掉（8-26、10-07 各删过一次 pg_tblspc），
#     删掉后 PG 启动报 could not open directory "pg_tblspc"
#   - 但 pg_tblspc 不能学其他目录放 .keep 占位文件：PG 会把里面每个条目当表空间
#     opendir，遇到普通文件直接 FATAL: could not open directory "pg_tblspc/.keep/..."
#   所以：其他 12 个目录用 .keep 占位（见 protect_pg_dirs.py），pg_tblspc 只做 mkdir -p 兜底
PGDATA_DIR="/opt/data/.pg0/instances/hindsight-embed-hermes/data"
if [ -d "$PGDATA_DIR" ]; then
  for d in pg_tblspc pg_commit_ts pg_dynshmem pg_logical/snapshots pg_logical/mappings \
           pg_notify pg_replslot pg_serial pg_snapshots pg_stat_tmp pg_twophase \
           pg_wal/archive_status pg_wal/summaries; do
    mkdir -p "$PGDATA_DIR/$d"
  done
  # pg_tblspc 保持干净：移除任何误放的占位文件
  rm -f "$PGDATA_DIR/pg_tblspc/.keep" 2>/dev/null || true
fi

BIN=/opt/data/.cache/uv/archive-v0/UvuKov5JptV1YgV0DscNQ/bin/hindsight-api
if [ ! -x "$BIN" ]; then
  BIN=$(command -v hindsight-api || echo "")
  [ -n "$BIN" ] || { echo "hindsight-api binary not found"; exit 1; }
fi

# 已运行则跳过（原来用 pgrep -f "hindsight_api.main --idle-timeout"，
# 但真实 argv 是 .../bin/hindsight-api --idle-timeout 300，永远匹配不上，
# 会导致重复拉起。改为直接探测端口。）
if curl -s -m 3 --noproxy '*' http://127.0.0.1:9177/health 2>/dev/null | grep -q '"status":"healthy"'; then
  echo "hindsight daemon already running"
  exit 0
fi

setsid nohup "$BIN" --idle-timeout 300 --port 9177 >> /opt/data/.hindsight/profiles/hermes.log 2>&1 &
echo "launched daemon pid $!"
sleep 20
curl -s --max-time 4 http://127.0.0.1:9177/health && echo " <- healthy" || echo "health check failed (still booting?)"
