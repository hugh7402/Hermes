#!/usr/bin/env python3
"""PikPak Inbox-JAV 看门狗（cron 入口，调用 jav_manager.py --watch）"""
import os, subprocess, time

FLAG_FILE = "/opt/data/PikPak/.watch_active"
IDLE_FILE = "/opt/data/PikPak/.watch_idle_since"
MANAGER = "/opt/data/jav_manager.py"
HERMES_VENV = "/opt/hermes/.venv/bin/python3"

# 检查 flag —— 不存在则休眠
if not os.path.exists(FLAG_FILE):
    exit(0)

# 运行管理器看门狗模式
result = subprocess.run(
    [HERMES_VENV, MANAGER, "--watch"],
    capture_output=True, text=True, timeout=7200
)

output = result.stdout.strip()
if output:
    print(output)
