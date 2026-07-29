# 批量 note_enhance 处理未标记笔记

## 适用场景

知识库有大量（200+篇）新入库笔记缺 tags/summary/related，
逐个手动跑太慢，需要批量自动处理。

## 核心约束

- 每个笔记 3 次 API 调用（摘要 + 标签 + 关联发现）
- deepseek-v4-flash 每次约 0.5-2s → 每个笔记约 1.5-6s
- API 无并行 → 只能顺序处理
- **文件路径含空格/特殊字符** → 不能走 shell 展开

## 批处理策略

### 错误做法（已踩坑）

```bash
# ❌ shell 展开分词错误
python3 note_enhance.py $(cat filelist.txt)
# ❌ xargs 同样分词错误
xargs python3 note_enhance.py < filelist.txt
# ❌ cmd line too long
python3 note_enhance.py /path/to/Obsidian Vault/concepts/...md ...
```

### 正确做法

用 Python subprocess 逐批传参：

```python
# batch_enhance.py — 核心模式
import subprocess
BATCH_SIZE = 10
TIMEOUT = 120  # 每批超时

for i in range(0, len(files), BATCH_SIZE):
    batch = files[i:i+BATCH_SIZE]
    r = subprocess.run(
        ['python3', '/opt/data/note_enhance.py'] + batch,
        capture_output=True, text=True, timeout=TIMEOUT
    )
```

### 分批大小与超时

| 文件类型 | 批次大小 | 超时 | 说明 |
|---------|---------|------|------|
| 普通笔记（长文本 ≤ 3K 字） | 10 | 120s | 默认 |
| 大文件（长篇报告 ≥ 10K 字） | 5 | 300s | API 处理长文本更慢 |
| 超大文件（≥ 50K 字） | 3 | 300s | 容易超时 |

## 注意

- note_enhance 会**覆盖**已有 tags/summary/related，不增量
- 去重：依赖 `.ingested` hash 日志，但 note_enhance 没有自己的去重
- 处理速度瓶颈在 API 延迟，不在 CPU
