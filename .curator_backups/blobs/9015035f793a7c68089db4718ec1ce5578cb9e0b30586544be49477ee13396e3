#!/usr/bin/env python3
"""
PikPak 智能看门狗 — 调度器（部署到 ~/.hermes/scripts/）
- 检查 flag 文件控制启停
- 无 flag → 静默退出（休眠态）
- 有 flag → 调用 pikpak_watch.py 检查新文件
- 1小时无新文件 → 自动清除 flag 进入休眠

用法：复制到 ~/.hermes/scripts/，创建 no_agent cron 任务
"""
import os, subprocess, time

WATCH_SCRIPT = os.path.expanduser("~/.hermes/scripts/pikpak_watch.py")
FLAG_FILE = "/opt/data/PikPak/.watch_active"
IDLE_FILE = "/opt/data/PikPak/.watch_idle_since"

# 1) 检查 flag —— 不存在则休眠
if not os.path.exists(FLAG_FILE):
    exit(0)

# 2) 运行看门狗脚本
result = subprocess.run(
    ["python3", WATCH_SCRIPT],
    capture_output=True, text=True, timeout=7200
)

output = result.stdout.strip()
had_new_files = bool(output and ("发现" in output or "完成" in output))

if had_new_files:
    # 刷新最后活跃时间
    with open(IDLE_FILE, "w") as f:
        f.write(str(time.time()))
    print(output)
    exit(0)

# 3) 没有新文件 → 检查是否超过 1 小时
if os.path.exists(IDLE_FILE):
    with open(IDLE_FILE) as f:
        last_active = float(f.read().strip())
    idle_minutes = (time.time() - last_active) / 60

    if idle_minutes >= 55:
        os.remove(IDLE_FILE)
        os.remove(FLAG_FILE)
        print("😴 Inbox-JAV 超过 1 小时无新文件，已进入休眠")
        print("   需要时告诉我「下载inbox-JAV」即可重新激活")
        exit(0)
else:
    with open(IDLE_FILE, "w") as f:
        f.write(str(time.time()))

exit(0)
