#!/bin/bash
# 下载订阅 → 解码 → 全量 javdb 测试+测速
cd /opt/data/.tmp_tests
timeout 40 curl -sL --max-time 35 "https://dasho.pqjc.site/api/v1/pq/53eca709b4fb562544949681e80cae21" -o /tmp/sub_new.b64 2>&1
echo "订阅下载: $(wc -c < /tmp/sub_new.b64) bytes"
python3 -c "
import base64
raw = open('/tmp/sub_new.b64','rb').read()
try:
    lines = [l for l in base64.b64decode(raw).decode().splitlines() if l.strip()]
except Exception:
    lines = raw.decode(errors='ignore').splitlines()
open('/tmp/sub_decoded_new.txt','w').write('\n'.join(lines))
print('节点数:', len(lines))
"
echo "=== 开始全量测试 ==="
cd /opt/data/skills/network/proxy-node-batch-test/scripts
python3 test_javdb_nodes.py /tmp/sub_decoded_new.txt --speed 2>&1
echo "ALL_TEST_DONE"
