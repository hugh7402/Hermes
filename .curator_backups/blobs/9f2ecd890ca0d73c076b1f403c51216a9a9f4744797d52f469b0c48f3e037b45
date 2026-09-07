#!/usr/bin/env python3
"""
PikPak 自动下载看门狗 — 底层下载器
- 扫描远程目录，对比本地记录，新文件并行拉取（最多 MAX_PER_RUN 个/次）
- 静默模式：无新文件时完全静默（0 token）
- 被 pikpak_watch_wrapper.py 上层包装器调用
- 支持断点续传（rclone 自带的 .partial 机制）

用法：
  直接运行：python3 pikpak_watch.py
  或由包装器调用：python3 pikpak_watch_wrapper.py

可定制变量（适配其他远程目录）：
  SRC  — 远程路径（如 /Inbox-JAV）
  DEST — 本地下载路径
  RECORD — 记录文件路径
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
r = subprocess.run(
    [RCLONE, "lsjson", f"{REMOTE}:{SRC}"],
    capture_output=True, text=True, timeout=120
)
if not r.stdout.strip():
    sys.exit(0)  # 空目录，静默

try:
    files = json.loads(r.stdout)
except json.JSONDecodeError:
    sys.exit(0)

# 找新文件（基于 文件名|大小|修改时间 唯一标识）
new = [
    (f["Name"], f"{f['Name']}|{f['Size']}|{f.get('ModTime','')}")
    for f in files if f["Size"] > 0
    and f"{f['Name']}|{f['Size']}|{f.get('ModTime','')}" not in downloaded
]

if not new:
    sys.exit(0)  # 无新文件，静默

batch = new[:MAX_PER_RUN]
print(f"📥 发现 {len(new)} 个新文件，本次下载 {len(batch)} 个")

# 写文件列表供 rclone --files-from
list_file = "/tmp/pikpak_batch.txt"
with open(list_file, "w") as f:
    for name, _ in batch:
        f.write(f"{SRC}/{name}\n")

# 一次并行下载（--transfers = 本次数量）
r = subprocess.run(
    [RCLONE, "copy", "--files-from", list_file,
     f"{REMOTE}:", DEST,
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
msg = f"✅ 完成: {succeed} 成功"
if failed:
    msg += f", {failed} 失败"
msg += f"，剩余 {len(new) - len(batch)} 个待下载"
print(msg)
