# 在线文档入库（腾讯文档/飞书等）

对于用户发的在线文档链接（腾讯文档、飞书文档、石墨文档等），常规的 `ingest_docs.py` 脚本无法直接处理，需要手动下载导出。

## 通用流程

### 1. 判断文档类型

| 平台 | 域名特征 | 导出方式 |
|------|---------|---------|
| 腾讯文档 | `docs.qq.com/doc/` | 公开链接可直接 curl 导出 PDF |
| 飞书文档 | `feishu.cn/doc/` 或 `lark-api` | 需要 API token |
| 石墨文档 | `shimo.im/` | 需登录 |
| 语雀 | `yuque.com/` | 需登录 |

### 2. 腾讯文档导出（最常用）

用户发的是腾讯文档公开分享链接（无需登录可查看），可以绕过浏览器直接导出 PDF：

```bash
# 导出 PDF
curl -sL -o "/path/to/output.pdf" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://docs.qq.com/doc/{DOC_ID}?download=1&format=pdf"
```

#### 导出 API 细节

- 格式参数：`?download=1&format=pdf`（PDF）或 `?download=1&format=docx`（Word）
- DOC_ID 即链接中的 `DWU1ZYXJBWUJIY3NE` 那一段
- 需要 `-H "User-Agent: ..."` 避免被拒绝
- 公开链接（"只能查看"）即可下载，无需登录

### 3. 检查导出文件

```python
import fitz
doc = fitz.open('/path/to/exported.pdf')
text = ''
for page in doc:
    text += page.get_text()

if len(text) > 50:
    # 有文字，直接入库
    pass
else:
    # 扫描件，需要 OCR
    subprocess.run(['/opt/hermes/.venv/bin/python3', 
                    '/opt/data/pdf_ocr.py', pdf_path], ...)
```

腾讯文档导出的 PDF 通常是扫描件（canvas 渲染），文字长度常 < 50 字符，**几乎都需要走 OCR 流程**。

### 4. 入库到 concepts/

1. 检查 `.ingested` 是否已处理（MD5 去重）
2. 如果已处理 → 跳过
3. 如果未处理：
   - 运行 OCR → 获取文本
   - 添加 `# 标题` 和 `> **原始文件**：` 元数据块
   - 写入 `concepts/{safe_name}.md`
   - 写入 `.ingested` 记录 hash
4. 调用 `note_enhance.py` 增强 frontmatter

### 5. 同时备份到 WebChat 目录

如果需要备份到每日入库队列（可选）：
```bash
# 注意：WebChat 目录是 root 属主，cp 会 Permission denied
# 直接走临时路径入库即可，不需要复制到备份目录
```

## 注意事项

- **浏览器自动化不可靠**：腾讯文档页面是 Canvas 渲染，且检测自动化脚本。优先尝试导出 API
- **公开链接优先**：如果用户发的是"只能查看"链接，可以直接导出。如果是"需要权限"链接，需要用户手动下载后发我
- **页数管理**：腾讯文档导出 PDF 通常页数较少（4-20页），OCR 一次跑完即可，不需要分批
- **容量检查**：导出前先 curl 检查 Content-Length，避免下载超大文件

## 版本对比：OCR PDF vs 原生 docx

**这是一个重要的质量陷阱。** 腾讯文档导出的 PDF 是 Canvas 渲染的扫描件，PaddleOCR 对其后几页（通常含表格、图表、排版复杂的页面）识别质量极差，输出大面积乱码。

### 真实案例（2026-06-25）

| 对比项 | OCR PDF 版 | 原生 docx 版 |
|--------|-----------|-------------|
| 有效字符 | ~1,590 | 5,769 |
| 内容覆盖 | 仅开头概要，第3-4页全乱码 | 完整的六章内容 + 数据表格 |
| 可用性 | ❌ 后几页含韩文/编码垃圾 | ✅ 所有章节可读 |

### 正确工作流

1. 用户发腾讯文档链接 → 先尝试导出 PDF 获取内容提纲
2. **同时向用户索要 docx 版本**（通过微信发送文件）
3. 收到 docx 后：提取全文比对 PDF OCR 版
4. 若 docx 版明显更完整（通常是）：覆盖替换 concepts/ 中的笔记，更新 `.ingested` hash
5. 重新运行 `note_enhance.py` 增强
6. 若用户明确指定「以 docx 为准」或「以 PDF 为准」，遵从其指示

### 替换 hash 的代码片段

```python
PROCESSED_LOG = '/opt/data/Obsidian Vault/Obsidian Vault/.ingested'
lines = Path(PROCESSED_LOG).read_text().strip().split('\n')
new_lines = [docx_hash if l == pdf_hash else l for l in lines]
Path(PROCESSED_LOG).write_text('\n'.join(new_lines) + '\n')
```
