#!/bin/bash
cd /opt/data/bin
curl -sL --max-time 100 --proxy http://127.0.0.1:10808 -H "User-Agent: Mozilla/5.0" \
  "https://downloads.rclone.org/rclone-current-linux-amd64.zip" -o /opt/data/.tmp_tests/rclone.zip
ls -la /opt/data/.tmp_tests/rclone.zip
python3 -c "
import zipfile, glob, shutil, os
z = zipfile.ZipFile('/opt/data/.tmp_tests/rclone.zip')
z.extractall('/opt/data/bin/rclone_tmp')
files = glob.glob('/opt/data/bin/rclone_tmp/*/rclone')
print('找到:', files)
assert files, 'no rclone binary in zip'
shutil.copy(files[0], '/opt/data/bin/rclone')
os.chmod('/opt/data/bin/rclone', 0o755)
print('已复制到 /opt/data/bin/rclone')
"
ls -la /opt/data/bin/rclone
/opt/data/bin/rclone version | head -2
echo "RCLONE_READY"
