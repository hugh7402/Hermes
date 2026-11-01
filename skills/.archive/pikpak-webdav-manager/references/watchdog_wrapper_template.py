"""
看门狗包装器模板 — 可复用于任意网盘的智能休眠模式

用法：
1. 复制此文件，修改 WATCH_SCRIPT / FLAG_FILE / IDLE_FILE / IDLE_TIMEOUT
2. 确保底层下载脚本存在（从 SRC 检查 → 下载到 DEST → 记录到 RECORD）
3. 创建 no_agent cron 任务，script 指向包装器
4. 初始状态不创建 .watch_active（默认休眠）
5. 用户激活时 touch .watch_active + cronjob run <id>
"""
import os, subprocess, time

# ===== 以下 4 个变量按需修改 =====
WATCH_SCRIPT = "/opt/data/scripts/my_watch.py"   # 底层下载器路径
FLAG_FILE = "/opt/data/.watch_active"             # 活跃标志文件
IDLE_FILE = "/opt/data/.watch_idle_since"         # 空闲时间戳文件
IDLE_TIMEOUT = 55  # 空闲超时（分钟）

# ==== 以下逻辑通用，无需修改 ====
if not os.path.exists(FLAG_FILE):
    exit(0)  # 休眠态 → 静默退出

result = subprocess.run(["python3", WATCH_SCRIPT],
    capture_output=True, text=True, timeout=7200)

output = result.stdout.strip()
had_new = bool(output and ("发现" in output or "完成" in output))

if had_new:
    with open(IDLE_FILE, "w") as f:
        f.write(str(time.time()))
    print(output)
    exit(0)

if os.path.exists(IDLE_FILE):
    with open(IDLE_FILE) as f:
        last_active = float(f.read().strip())
    if (time.time() - last_active) / 60 >= IDLE_TIMEOUT:
        os.remove(IDLE_FILE)
        os.remove(FLAG_FILE)
        print("😴 超过1小时无新文件，已进入休眠")
        exit(0)
else:
    with open(IDLE_FILE, "w") as f:
        f.write(str(time.time()))

exit(0)
