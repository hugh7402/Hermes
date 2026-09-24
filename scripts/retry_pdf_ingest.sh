#!/bin/bash
# 扫描件 PDF 补入库重试（cron 每30分钟）
# 逻辑：SiliconFlow OCR 不可用（402 余额不足/网络）时完全静默、不产出任何 stdout；
#      恢复后自动 OCR 入库 4/5/6 三个 Token 扫描件，全部完成输出一条简报并写 done 标记，
#      之后本任务永远静默退出。
# 依赖：/opt/data/scripts/patch_ocr_ingest.py（含质量门，防止 402 空壳污染知识库）
cd /opt/data || exit 0

export PATH="/opt/data/ocr_venv/bin:/opt/data/.venv/bin:$PATH"

echo "=== $(date '+%Y-%m-%d %H:%M') 检查 ===" >> /tmp/retry_pdf_ingest.log

exec /opt/data/ocr_venv/bin/python3 /opt/data/scripts/patch_ocr_ingest.py
