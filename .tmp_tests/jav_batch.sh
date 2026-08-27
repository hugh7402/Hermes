#!/bin/bash
# JAV 批量 Phase 1-2: javdb 搜磁链 → PikPak 离线 → 清理广告 → 重命名
cd /opt/data
export PATH=/opt/data/.venv/bin:$PATH
exec python3 jav_manager.py --no-sync JUR-794 GARA-025 IPZZ-901 IPZZ-914 JUR-837 DLDSS-525 JUFE-628 2>&1
