# 大扫描件 OCR 恢复流程（ingest 400s 超时场景）

2026-08-23 实测：57 页全图扫描件（10.7MB）在 ingest_docs.py 里 OCR 超时（400s 硬限）。
单进程 PaddleOCR-VL 约 20-45s/页（API 偶发 120s 超时需重试），57 页单跑要 40+ 分钟，必然超时。

## 正确流程：分段并发 → 失败页补录 → 合并清洗 → 手动入库

### 1. 探测
写 probe 脚本（write_file 落盘），`export PATH=/opt/data/ocr_venv/bin:$PATH && python3 probe.py` 运行，
确认页数 / 图片页数 / 尺寸（fitz：`doc.page_count`、`doc[i].get_images()`）。

### 2. 分段并发 OCR
pdf_ocr.py 支持 start_page/end_page（0-based，end 不含）。57 页分 4 段并发：

```bash
export PATH=/opt/data/ocr_venv/bin:$PATH && python3 /opt/data/pdf_ocr.py "<pdf>" 0 15 > /tmp/ocr_p1.txt 2>&1
# 另三路：15 30 / 30 45 / 45 57，各 background=true + notify_on_complete
```

4 并发 ≈ 3.5 页/分钟，57 页约 15 分钟跑完。

### 3. 失败页补录
- 统计：`grep -c "✓" 分片文件` 得成功页数；失败页在正文里是 `[第 N 页 OCR 失败]` 占位。
- 写补录脚本：对失败页逐一 `get_pixmap(dpi=200)` → 调 API，最多 3 次重试
  （HTTPError 等 30s，其他异常等 10s），成功后存 JSON 供合并时覆盖。
- 实测 14 个失败页全部补回。

### 4. 合并（关键坑：pdf_ocr.py 输出格式）
stdout 结构 = **先全部进度行（`    第 N/57 页... ✓ (N 字)`），最后一次性打印正文**。
正文段按页序排列、段间 `\n\n---\n\n` 分隔、失败页为 `[第 N 页 OCR 失败]`。

- 正确解析：跳过开头进度行块（📸 行 + `^第 \d+/57 页` 行），从第一个正文行开始，
  按 `---` 分割 → 段落 k 对应第 start+k+1 页。
- ❌ 别把进度行当页锚点去逐行匹配正文（进度行与正文段无对应关系，会解析出全空页）。

### 5. 清洗 PaddleOCR-VL 伪影
- 剥离定位标记：`re.sub(r'<\|LOC_\d+\|>', '', text)`，兜底 `<\|[^|]*\|>`。
- 封面/图表页会有乱码幻觉（俄/韩/英混排）——免费模型正常现象，保留即可，别为它重 OCR。
- 清理后 82K 字 → 47K 字（去掉标记和空段）。

### 6. 手动入库（绕过 ingest_docs.py 400s 限时）
ingest_docs.py 对 OCR 子进程硬编码 timeout=400，大扫描件永远走不完。手动执行其入库逻辑：

1. **safe_name 必须 `stem + '.md'`**：`f.name.rsplit('.', 1)[0] + '.md'`，别保留原扩展名
   （2026-08-23 踩过：直接用了含 .pdf 的完整文件名，concepts/ 里生成 `.pdf` 后缀的 md，需 mv 修正，
   且 note_enhance 已跑过，重命名即可）。
2. 无 `# ` 标题则补 `# {base_title}` + source 行；有则插到首个 H1 后（与 ingest_docs.py save_note 一致）。
3. `python3 /opt/data/note_enhance.py <name>.md`（cwd=concepts/，timeout=300）。
4. mark_processed：md5 写入 `{VAULT}/.ingested`（防 cron 重复处理）。
5. 更新 index.md（`- [[{title}]] — 自动摄入` 插到 `## 实体` 前）+ log.md。

## 验证
- 重命名后确认 concepts/ 下是 `.md` 后缀、index.md 有条目、.ingested 有 hash、log.md 有记录。
- 下次 cron 不会重复处理该文件。
