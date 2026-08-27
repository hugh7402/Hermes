#!/bin/bash
# 1) 修正磁链（相对路径避免守卫 bug）
cd /opt/data/.tmp_tests
export PATH=/opt/data/.venv/bin:$PATH
echo "===== [1/2] 修正磁链 ====="
python3 fix_magnets.py 2>&1
# 2) 新番号 Phase 1-2
cd /opt/data
echo "===== [2/2] CAWB-025 + DVMM-415 + IPZZ-879 ====="
python3 jav_manager.py --no-sync CAWB-025 DVMM-415 IPZZ-879 2>&1
echo "ALL_DONE"
