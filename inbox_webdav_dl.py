#!/usr/bin/env python3
"""Inbox-JAV WebDAV 并发下载器 — 13 个真实文件并发测试+下载
边测边下：13 路 rclone 独立进程，实时采样速度
"""
import json, os, sys, time, subprocess, shutil

MANIFEST = '/tmp/inbox_videos.json'
DEST_ROOT = '/opt/data/PikPak/Inbox-JAV'
RCLONE = '/tmp/rclone'

def main():
    files = json.load(open(MANIFEST))
    print(f"任务: {len(files)} 个文件, {sum(f['size'] for f in files)/1024**3:.2f} GB")
    
    # 目标目录
    os.makedirs(DEST_ROOT, exist_ok=True)
    
    # 跳过已存在（≥99%）
    todo = []
    for f in files:
        dest = os.path.join(DEST_ROOT, f['name'])
        if os.path.exists(dest) and os.path.getsize(dest) >= f['size'] * 0.99:
            print(f"⏭️ 已存在: {f['name'][:40]}")
        else:
            todo.append(f)
    
    print(f"待下载: {len(todo)} 个, 并发 {len(todo)} 全开\n")
    
    # 启动全部 rclone 进程
    procs = []
    dirs = []
    for i, f in enumerate(todo):
        d = os.path.join(DEST_ROOT)
        os.makedirs(d, exist_ok=True)
        p = subprocess.Popen(
            [RCLONE, 'copy', f'pikpak:Inbox-JAV/{f["name"]}', d,
             '--buffer-size=128M', '--multi-thread-streams=0'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        procs.append(p)
        dirs.append(d)
        print(f"  [{i+1}/{len(todo)}] ⬇️ {f['name'][:45]} ({f['size']/1024**2:.0f}MB)")
    
    # 监控循环：每 5 秒采样速度
    t0 = time.time()
    last_total = 0
    samples = []
    completed = set()
    
    while True:
        time.sleep(5)
        dt = time.time() - t0
        
        # 总下载量（真实字节）
        total = 0
        for f in todo:
            dest = os.path.join(DEST_ROOT, f['name'])
            if os.path.exists(dest):
                total += os.path.getsize(dest)
        
        # 当前完成的文件数
        done_now = sum(1 for f in todo if os.path.exists(os.path.join(DEST_ROOT, f['name'])) 
                       and os.path.getsize(os.path.join(DEST_ROOT, f['name'])) >= f['size'] * 0.99)
        
        inst = (total - last_total) / 5 / 1024 / 1024
        last_total = total
        samples.append(inst)
        
        # 进程存活数
        alive = sum(1 for p in procs if p.poll() is None)
        
        print(f"  [{dt:.0f}s] 总 {total/1024**3:.2f}/{sum(f['size'] for f in todo)/1024**3:.2f} GB | "
              f"瞬时 {inst:.1f} MB/s | 完成 {done_now}/{len(todo)} | 进程 {alive}", flush=True)
        
        if alive == 0 and done_now == len(todo):
            break
        if dt > 7200:  # 2 小时上限
            print("超时退出")
            break
    
    # 汇总
    avg = sum(samples) / len(samples) if samples else 0
    peak = max(samples) if samples else 0
    print(f"\n=== 完成: {done_now}/{len(todo)} ===")
    print(f"平均速度 {avg:.1f} MB/s, 峰值 {peak:.1f} MB/s, 总耗时 {dt/60:.1f}min")
    
    # 失败进程
    for i, p in enumerate(procs):
        if p.poll() is not None and p.returncode != 0:
            print(f"  ❌ 失败: {todo[i]['name'][:40]} rc={p.returncode}")

if __name__ == '__main__':
    main()
