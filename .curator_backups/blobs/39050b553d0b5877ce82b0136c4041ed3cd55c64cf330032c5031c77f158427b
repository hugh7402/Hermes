#!/usr/bin/env python3
"""
PikPak 智能看门狗包装器（no_agent 纯脚本）

行为逻辑：
1. 检查 flag 文件 → 不存在则完全静默退出（0 token）
2. 运行底层下载器检查新文件
3. 记录最后发现新文件的时间戳
4. 超过 1 小时没有新文件 → 清除 flag，进入休眠
5. 用户说"下载inbox-JAV" → 创建 flag 文件激活它

可作为模板：修改 WATCH_SCRIPT / FLAG_FILE / IDLE_TIMEOUT 适配其他网盘
"""
import os, subprocess, time

WATCH_SCRIPT = "/opt/data/scripts/pikpak_watch.py"  # 底层下载器路径
FLAG_FILE = "/opt/data/PikPak/.watch_active"          # 活跃标志
IDLE_FILE = "/opt/data/PikPak/.watch_idle_since"      # 空闲时间戳
IDLE_TIMEOUT = 55  # 空闲超过此分钟数后自动休眠（留5分钟余量）

# 1) 检查 flag —— 不存在则休眠
if not os.path.exists(FLAG_FILE):
    exit(0)  # 完全静默退出，0 token

# 2) 运行看门狗脚本
result = subprocess.run(
    ["python3", WATCH_SCRIPT],
    capture_output=True, text=True, timeout=7200
)

output = result.stdout.strip()
had_new_files = output and ("发现" in output or "完成" in output)

if had_new_files:
    # 有新文件 → 刷新最后活跃时间
    with open(IDLE_FILE, "w") as f:
        f.write(str(time.time()))
    print(output)
    exit(0)

# 3) 没有新文件 → 检查是否超过空闲阈值
if os.path.exists(IDLE_FILE):
    with open(IDLE_FILE) as f:
        last_active = float(f.read().strip())
    idle_minutes = (time.time() - last_active) / 60

    if idle_minutes >= IDLE_TIMEOUT:
        os.remove(IDLE_FILE)
        os.remove(FLAG_FILE)
        print("😴 超过1小时无新文件，已进入休眠")
        print("   需要时通知我即可重新激活")
        exit(0)
else:
    # 首次静默运行，记录时间但不休眠
    with open(IDLE_FILE, "w") as f:
        f.write(str(time.time()))

exit(0)
