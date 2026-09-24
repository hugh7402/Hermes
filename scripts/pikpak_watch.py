#!/usr/bin/env python3
"""
PikPak Inbox-JAV 自动下载看门狗（静默模式）
- 没新文件 → 完全静默，0 token
- 有新文件 → 推送下载结果
"""
import os, subprocess, json, sys

RCLONE = "/tmp/rclone"
REMOTE = "pikpak"
SRC = "/Inbox-JAV"
DEST = "/opt/data/PikPak/Inbox-JAV"
RECORD = "/opt/data/PikPak/.inbox_record.json"
MAX_PER_RUN = 5

os.makedirs(DEST, exist_ok=True)

# 读取已下载记录
downloaded = set()
if os.path.exists(RECORD):
    with open(RECORD) as f:
        downloaded = set(json.load(f))

# 获取远程文件列表
r = subprocess.run([RCLONE, "lsjson", f"{REMOTE}:{SRC}"],
                   capture_output=True, text=True, timeout=120)
if not r.stdout.strip():
    # 空目录，静默退出
    sys.exit(0)

try:
    files = json.loads(r.stdout)
except json.JSONDecodeError:
    sys.exit(0)

# 找新文件
new = [(f["Name"], f"{f['Name']}|{f['Size']}|{f.get('ModTime','')}")
       for f in files if f["Size"] > 0
       and f"{f['Name']}|{f['Size']}|{f.get('ModTime','')}" not in downloaded]

if not new:
    # 没有新文件 → 完全静默
    sys.exit(0)

batch = new[:MAX_PER_RUN]
print(f"📥 Inbox-JAV 发现 {len(new)} 个新文件，本次下载 {len(batch)} 个")

# 写文件列表（只用文件名，不带路径前缀）
list_file = "/tmp/pikpak_batch.txt"
with open(list_file, "w") as f:
    for name, _ in batch:
        f.write(f"{name}\n")

# 一次并行下载
r = subprocess.run(
    [RCLONE, "copy", "--files-from", list_file,
     f"{REMOTE}:{SRC}", DEST,
     "--transfers", str(len(batch)),
     "--checkers", "16",
     "--retries", "2", "--retries-sleep", "5s",
     "--checksum"],
    capture_output=True, text=True, timeout=7200
)

# 记录成功下载的
succeed = 0
for name, key in batch:
    dst = os.path.join(DEST, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        downloaded.add(key)
        succeed += 1

with open(RECORD, "w") as f:
    json.dump(list(downloaded), f, ensure_ascii=False)

failed = len(batch) - succeed
print(f"✅ 完成: {succeed} 成功", end="")
if failed:
    print(f", {failed} 失败", end="")
print(f"，剩余 {len(new) - len(batch)} 个待下载")
