#!/usr/bin/env python3
"""AI短剧下载监控 — 检查并发是否正常、是否卡住、进度"""
import os, subprocess, time, json

LOG = '/tmp/ai_drama_dl.log'
PID_FILE = '/tmp/ai_drama_dl.pid'

def main():
    # 1. 主进程是否在
    r = subprocess.run(['pgrep', '-f', 'ai_drama_dl.py'], capture_output=True, text=True, timeout=10)
    main_pids = [p for p in r.stdout.strip().split('\n') if p]
    if not main_pids:
        print("❌ 下载进程已退出！")
        return

    # 2. aria2 并发数
    r2 = subprocess.run(['pgrep', '-f', 'aria2c'], capture_output=True, text=True, timeout=10)
    aria_count = len([p for p in r2.stdout.strip().split('\n') if p])

    # 3. 日志最后修改时间（判断是否卡住）
    if os.path.exists(LOG):
        mtime = os.path.getmtime(LOG)
        age = time.time() - mtime
    else:
        age = -1

    # 4. 进度
    done = 0
    if os.path.exists(LOG):
        with open(LOG, errors='ignore') as f:
            content = f.read()
        import re
        m = re.findall(r'\[(\d+)/1248\]', content)
        if m:
            done = int(m[-1])
        # 完成数
        ok = len(re.findall(r'✅', content))
        fail = len(re.findall(r'❌', content))

    # 5. 已下载大小
    total = 0
    r3 = subprocess.run(['du', '-sb', '/opt/data/PikPak/AI短剧'], capture_output=True, text=True, timeout=30)
    if r3.returncode == 0:
        total = int(r3.stdout.split()[0])

    # 输出状态（非零退出 → 异常通知）
    status = []
    if aria_count == 0:
        status.append(f"⚠️ aria2 并发 0（应≥1）")
    if age > 300:
        status.append(f"⚠️ 日志 {age/60:.0f} 分钟未更新，可能卡住")
    if main_pids and not aria_count:
        status.append(f"⚠️ 主进程在但无下载活动")

    if status:
        print(" ".join(status))
        return  # exit 0 但输出警告

    # 正常 → 静默（no_agent cron: 空输出=静默）
    # print(f"进度 {done}/1248, aria2 x{aria_count}, 已下载 {total/1024**3:.1f}GB")

if __name__ == '__main__':
    main()
