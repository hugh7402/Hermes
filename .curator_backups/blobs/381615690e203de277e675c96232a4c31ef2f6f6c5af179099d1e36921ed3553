# 自制 PikPak 看门狗指南

为 PikPak 任意目录设置智能自动下载。

## 步骤

### 1. 复制底层下载器

```bash
cp scripts/pikpak_watch.py scripts/mydir_watch.py
```

修改 `mydir_watch.py` 中的：
- `SRC = "/Inbox-JAV"` → 改为目标目录（如 `"/电影"`）
- `DEST = "/opt/data/PikPak/Inbox-JAV"` → 改为本地目标
- `RECORD = "/opt/data/PikPak/.inbox_record.json"` → 改为不同记录文件
- `MAX_PER_RUN = 5` → 按需调整

### 2. 创建 Cron 任务

```bash
hermes cronjob create \
  --name "PikPak 电影自动下载" \
  --schedule "every 10m" \
  --script "pikpak_watch_wrapper.py" \
  --no-agent
```

### 3. 激活

```bash
echo "active" > /opt/data/PikPak/.watch_active
# 或创建独立 flag：echo "active" > /opt/data/PikPak/.watch_movies
# 同时修改包装器的 FLAG_FILE 指向新 flag
```

### 4. 验证

```bash
cronjob run <job_id>
# 检查 cron 输出
cat /opt/data/cron/output/<job_id>/latest.md
```
