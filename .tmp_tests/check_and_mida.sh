#!/bin/bash
cd /opt/data/.tmp_tests
export PATH=/opt/data/.venv/bin:$PATH
echo "===== [1/2] 检查+清理残留 ====="
python3 check_inbox.py 2>&1
echo "===== [2/2] MIDA-693 Phase 1-2 ====="
cd /opt/data
python3 jav_manager.py --no-sync MIDA-693 2>&1
echo "ALL_DONE"
