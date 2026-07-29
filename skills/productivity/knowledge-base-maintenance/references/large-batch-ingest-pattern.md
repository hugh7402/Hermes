# 大批量文档分批入库模式

## 场景

`WebChat BackUp/文档/` 下新增大量文件（如 300+ PDF，其中 78% 扫描件），需要在指定日期前完整入库。

## 核心约束

- **no_agent cron 硬限制 120s**：脚本必须 ≤ 120s 完成，否则被调度器 `SIGTERM`。OCR 大 PDF 一个就可能超时。
- **解决方案**：切 Agent 模式 cron（用 prompt 驱动终端执行脚本），或每次只处理 1 个文件。
- **哈希去重**：共用 `$VAULT/.ingested`（MD5），与 9:00 自动入库不冲突。

## 策略

1. **区分文本型 vs 扫描件**：先用 pymupdf 试提文字，`len(text) < 50` 才切 OCR
2. **每批文件数**：文本型可 5-20 个一批；扫描件降到 **3 个**一批（每文件最长 10 分钟 OCR）
3. **超时兜底**：`TIMEOUT_PER_FILE = 600s`，单文件超时直接跳过，记录 hash 防重试
4. **空文件处理**：零字节 PDF 抛出 `fitz.EmptyFileError`，检查 `os.path.getsize() > 0` 后跳过

## cron 配置示例

```
# Agent 模式（推荐 — 无 120s 限制）
cron create name="my-batch-ingest" schedule="0 7,11,15,19 * * *" \
  prompt="运行 /path/to/batch_ingest.py，报告入库数量和剩余"
```

## 进度估算

- 每日处理量 = 9:00 主管道(20 个) + 专用管道(每批 3 个 × 4 次 = 12 个) = **32 个/天**
- 318 个文件 ÷ 32 ≈ **10 天**清完
- 适用于有时间限制的批量入库需求
