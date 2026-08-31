#!/bin/bash
cd /opt/data/.tmp_tests
export PATH=/opt/data/.venv/bin:$PATH
python3 finalize_batch.py 2>&1
echo "FINALIZE_DONE"
