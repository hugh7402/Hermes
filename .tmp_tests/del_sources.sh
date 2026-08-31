#!/bin/bash
cd /opt/data/.tmp_tests
export PATH=/opt/data/.venv/bin:$PATH
# 先找 JUR-794 字幕实际文件名
echo "=== Inbox-JAV 字幕文件 ==="
ls -la /opt/data/PikPak/Inbox-JAV/*.srt 2>/dev/null
echo "=== 删 PikPak 源 ==="
python3 del_sources.py 2>&1
echo "ALL_DONE"
