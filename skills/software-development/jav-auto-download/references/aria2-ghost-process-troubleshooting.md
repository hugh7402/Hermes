# Aria2 幽灵进程 & 腐败文件排查记录

## 现象

下载 MFYD-144.mp4（8.1GB）时：

1. 文件**瞬间出现**在目录（7.6GB），但 ffprobe 报 `moov atom not found`
2. 即使删除后重新用 aria2 下载，同样的问题重复出现
3. 新启动的 aria2 进程**没有任何 socket 连接**和文件 fd，但文件却自动出现
4. `ls -lh` 显示的文件大小与 PikPak 报告的完全一致

## 根因

**双层进程残留：**

```
你执行: kill 16082 (bash wrapper)
                │
                ▼
bash 16082 已死  ← Ss 状态（会话 leader，睡眠）
                │
     aria2 16086 仍存活！ ← S 状态（9.8% CPU 活跃下载）
                │
                ▼
        fd 5 → MFYD-144.mp4 (deleted)
                │
                ▼
      文件从目录入口 unlink，但 inode 仍被写入
```

1. 第一次用 `kill 16082` 只杀了 bash 包装器（`/usr/bin/bash -lic set +m; export LD_LIBRARY_PATH...`）
2. 实际 aria2 子进程（PID 16086）继续运行，持有已删除文件的 fd
3. 当你 `rm -f MFYD-144.mp4` 后，启动新 aria2 —— 新进程尝试创建同名文件
4. 旧进程继续通过已删除的 fd 写入底层 inode
5. 新进程也可能写入同一 inode（取决于文件系统实现）
6. 最终文件存在但数据属于多个不完整写入 → `moov atom not found`

## 排查步骤

```bash
# 1. 检查所有 aria2 进程（不只是 bash 包装器）
ps aux | grep aria2c

# 2. 检查进程的打开文件描述符
ls -la /proc/<PID>/fd/

# 3. 查找 "(deleted)" 标记的文件 → 幽灵进程
# 正常: /opt/data/PikPak/Inbox-JAV/MFYD-144.mp4
# 异常: /opt/data/PikPak/Inbox-JAV/MFYD-144.mp4 (deleted)

# 4. 检查 aria2 是否有活跃网络连接
ls -la /proc/<PID>/fd/ | grep -c socket
# =0 说明没有在下载

# 5. 检查进程状态
cat /proc/<PID>/stat | awk '{print "state=" $3}'
# S = 睡眠（等待中）, R = 运行中（正常下载）

# 6. 校验文件完整性（唯一可靠方法）
ffprobe -v error -show_entries format=duration -of csv=p=0 file.mp4
# 输出数值 → OK
# "moov atom not found" → 腐败，需重下
```

## 关键陷阱：pkill 杀死新启动的 aria2

**这是一个特别容易犯的错误：** 当你先启动 aria2，然后跑 `pkill -f aria2c`（意图清理旧进程），你实际杀死了刚启动的新进程。

错误顺序：
```bash
# 错误：先启动新 aria2
aria2c --dir=/tmp/dl --input-file=/tmp/input.txt &
sleep 3

# 然后 pkill 旧进程（错误！）
pkill -f aria2c      # 杀死了刚启动的笔记本 aria2！
sleep 1
rm -f file.mp4       # 删除了 aria2 正在写入的文件
# aria2 子进程可能没死透，写入 (deleted) inode
```

正确顺序：
```bash
# 正确：先彻底杀旧进程
pkill -f aria2c 2>/dev/null; sleep 1
ps aux | grep aria2c || echo "clean"
rm -f /opt/data/PikPak/Inbox-JAV/*.aria2

# 再启动新下载
aria2c --dir=/tmp/dl --input-file=/tmp/input.txt
```

**黄金法则：** 任何时候要对 aria2 做清理操作（删除文件、重启动），必须先确认所有 aria2 进程已死。用 `notify_on_complete=true` 启动 aria2，等待它自然完成，期间绝不对下载目录做任何操作。

## 正确清理步骤

```bash
# 1. 杀所有 aria2（不要只杀 bash 包装器）
pkill -f aria2c
# 或
kill $(pgrep -f aria2c)

# 2. 确认无残留
ps aux | grep aria2c || echo "clean"

# 3. 清理 .aria2 控制文件
rm -f /opt/data/PikPak/Inbox-JAV/*.aria2

# 4. 删腐败文件 + sync
rm -f /opt/data/PikPak/Inbox-JAV/MFYD-144.mp4
sync
sleep 2

# 5. 验证文件已真正删除
ls /opt/data/PikPak/Inbox-JAV/MFYD-144.mp4 2>/dev/null || echo "gone"
```

## 替代方案（aria2 故障时的兜底）

当 aria2 反复出问题时，改用 curl 单线程下载：

```bash
# 1. 获取新 URL（必须有）
cd /opt/data && FRESH_URL=$(/opt/hermes/.venv/bin/python3 -c "
import json, asyncio, sys
sys.path.insert(0, '/opt/hermes/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi
async def get():
    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)
    info = await api.get_download_url('FILE_ID_HERE')
    print(info.get('web_content_link', ''))
asyncio.run(get())
")

# 2. 下载到 /tmp（避免目标目录的 fd 冲突）
#    -C - 启用断点续传
#    --max-time 600 最大等 10 分钟
curl -L -o /tmp/FILE.mp4 -C - --max-time 600 "$FRESH_URL"

# 3. 校验
ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/FILE.mp4

# 4. 合格再移动
mv /tmp/FILE.mp4 /opt/data/PikPak/Inbox-JAV/FILE.mp4
```

缺点：单线程速度 2-3 MB/s（8GB 约 50 分钟），但可靠性最高。

## 验证

- aria2 下载时，`/proc/<PID>/fd/` 应有 socket 连接（≥4）和指向 mp4 文件的 fd
- `ls -lh` 的速度增长应与网络带宽匹配（10 MB/s = 600 MB/分钟，不会是 7.6GB/秒）
- 任何"瞬间完成"的大文件下载都是红旗信号
