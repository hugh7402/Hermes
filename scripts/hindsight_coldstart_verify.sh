#!/bin/bash
# Hindsight 冷启动验证（避免命令行自匹配）
DATA=/opt/data/.pg0/instances/hindsight-embed-hermes/data

echo "═══ 当前进程 ═══"
ps -eo pid,etimes,cmd 2>/dev/null | grep -E 'bin/hindsight' | grep -v grep | cut -c1-110 | sed 's/^/  /'
ps -eo pid,etimes,cmd 2>/dev/null | grep -E 'embed-hermes' | grep -v grep | grep -v bash | cut -c1-110 | sed 's/^/  /'

echo ""
echo "═══ health ═══"
R=$(timeout 5 curl -s --noproxy '*' http://127.0.0.1:9177/health 2>/dev/null)
echo "  ${R:-000（未运行）}"

echo ""
echo "═══ 模拟 disk-cleanup 删掉 pg_tblspc ═══"
if [ -d "$DATA/pg_tblspc" ]; then
  if rmdir "$DATA/pg_tblspc" 2>/dev/null; then
    echo "  已删除 pg_tblspc（模拟事故）"
  else
    echo "  pg_tblspc 非空，无法 rmdir"
  fi
fi
[ -d "$DATA/pg_tblspc" ] && echo "  仍存在" || echo "  确认：pg_tblspc 不存在"

echo ""
echo "═══ 用补丁脚本拉起 ═══"
timeout 150 bash /opt/data/scripts/hindsight_start.sh 2>&1 | sed 's/^/  /'

echo ""
echo "═══ 健康检查 ═══"
for i in $(seq 1 8); do
  R=$(timeout 6 curl -s --noproxy '*' http://127.0.0.1:9177/health 2>/dev/null)
  if [ -n "$R" ]; then echo "  [$i] OK $R"; break; fi
  echo "  [$i] $(date +%H:%M:%S) 未就绪"
  sleep 10
done

echo ""
echo "  pg_tblspc 重建: $([ -d "$DATA/pg_tblspc" ] && echo YES || echo NO)"
echo "  pg_tblspc 条目数: $(ls -A "$DATA/pg_tblspc" 2>/dev/null | wc -l)"
echo "  其他目录 .keep 数: $(find "$DATA" -name '.keep' 2>/dev/null | wc -l)"
