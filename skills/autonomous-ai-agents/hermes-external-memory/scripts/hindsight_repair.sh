#!/bin/bash
# Hindsight 一键修复 + 验证（幂等；永不删实例数据）
#
# 何时跑：hindsight_retain / recall 卡到 420s 超时、daemon 起不来、/health 非 200
# 依据：hermes-external-memory skill —— 最常见根因是「缺 PG 标准目录」
#       （PG 起不来时 LLM 配置再正确，retain 也照样超时；且日志会骗你）
# 2026-10-07 实跑验证：补 11 个目录后 /health 由 000 转 200 healthy。
set -u

PGD=/opt/data/.pg0/instances/hindsight-embed-hermes/data
[ -d "$PGD" ] || PGD=$(ls -d /opt/data/.pg0/instances/*/data 2>/dev/null | head -1)

echo "════ ① PG 数据目录 ════"
if [ -z "${PGD:-}" ] || [ ! -d "$PGD" ]; then
  echo "  ❌ 未找到实例目录。现有实例："
  ls -la /opt/data/.pg0/instances/ 2>/dev/null
  exit 1
fi
echo "  ✅ $PGD"

echo ""
echo "════ ② 补齐 PG 标准目录（幂等、无损；切勿删实例重建）════"
for d in pg_commit_ts pg_dynshmem pg_notify pg_replslot pg_serial pg_snapshots \
         pg_stat_tmp pg_tblspc pg_twophase pg_logical/snapshots pg_logical/mappings; do
  if [ -d "$PGD/$d" ]; then echo "  ✓ 已有 $d"; else mkdir -p "$PGD/$d" && echo "  ⊕ 新建 $d"; fi
done

echo ""
echo "════ ③ 另两个 PG 根因自查 ════"
ls -d /opt/data/.pg0/icu70/usr/lib/x86_64-linux-gnu >/dev/null 2>&1 \
  && echo "  ✅ libicu70 已解包" \
  || echo "  ⚠️ 缺 libicu70 —— 见 references/hindsight-daemon-recovery.md"
ls /opt/data/.pg0/installation/*/bin/postgres.real >/dev/null 2>&1 \
  && echo "  ✅ postgres.real 在位" \
  || echo "  ⚠️ 缺 postgres.real —— 见 references/hindsight-daemon-recovery.md"

echo ""
echo "════ ④ 清空 daemon + 孤儿 postgres（交给 dashboard 重拉）════"
for p in $(ps -eo pid,cmd | awk '/[h]indsight-api|[p]ostgres\.real|[u]v tool uvx hindsight/ {print $1}'); do
  kill -9 "$p" 2>/dev/null && echo "  killed $p"
done
sleep 3

echo ""
echo "════ ⑤ 等 dashboard 重拉（最多 180s，/health 转 200 即成功）════"
ok=0
for i in $(seq 1 18); do
  sleep 10
  code=$(timeout 8 curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9177/health 2>/dev/null)
  echo "  [$((i*10))s] /health=$code"
  if [ "$code" = "200" ]; then ok=1; break; fi
done

echo ""
echo "════ ⑥ /health ════"
timeout 10 curl -s http://127.0.0.1:9177/health; echo ""

cat <<'EOF'

════ 验收（唯一可信标准）════
  1. hindsight_retain 存一条 → 期望 "Memory stored successfully"（不再是 420s 超时）
  2. hindsight_recall 用刚存内容的关键词检索 → 期望新记忆排在最前
  ⚠️ 仅看日志出现 "Connection verified" 不算通过：LLM 通但 PG 没起来时 retain 照样超时。
EOF

if [ "$ok" = "1" ]; then echo "✅ /health 已 healthy，继续上面两步验收"; else echo "❌ 180s 内 /health 未转 200，见 references/hindsight-daemon-recovery.md"; exit 2; fi
