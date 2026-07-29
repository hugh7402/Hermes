# SiliconFlow OCR 流水线

使用 SiliconFlow 免费 API（PaddleOCR-VL-1.5）做扫描件 PDF OCR 的完整方案。

> **2026-06-21 更新**：新增分批 OCR + 断点续传策略。大 PDF 不再截断，改用 30页/批逐步跑完。

## 场景

pymupdf / marker-pdf 对扫描件 PDF 提取为空（0 字符）时，通过视觉大模型 API 做页面截图 OCR。

## 核心脚本：pdf_ocr.py

支持分批 OCR，用法：

```bash
# 全量 OCR（小文件）
/opt/hermes/.venv/bin/python3 /opt/data/pdf_ocr.py <pdf_path>

# 分批 OCR（大文件，每次30页）
/opt/hermes/.venv/bin/python3 /opt/data/pdf_ocr.py <pdf_path> 0 30   # 第0~29页
/opt/hermes/.venv/bin/python3 /opt/data/pdf_ocr.py <pdf_path> 30 60  # 第30~59页
```

脚本在末尾会输出继续命令提示。

## 分批 OCR 策略（大扫描件专用）

**问题**：取消 MAX_OCR_PAGES=30 限制后，>80 页扫描件逐页 OCR 在 400s subprocess timeout 内无法完成。

**策略**：不截断、不跳过，30页/批 + 断点续传逐步跑完。用 `batch_ocr_remaining.py` 自动管理。

### batch_ocr_remaining.py

路径：`/opt/data/batch_ocr_remaining.py`

功能：
- 一次处理 5 个大 PDF，每次 OCR 30 页
- 进度保存在 `/opt/data/.ocr_progress.json`
- 批处理完成后自动标记 hash 到 `.ingested`
- 断点续传：中断后重跑自动从上次位置继续

### 5个大PDF实测数据（2026-06-21）

| PDF | 页数 | 批次 | 总用时 | 总字数 |
|-----|------|------|--------|--------|
| 1.扬州数据局《人工智能基础知识》 | 134 | 3批 | ~12min | 289,693 |
| 3.《人工智能治理案例集》 | 456 | 15批 | ~60min | 1,937,770 |
| 7.AI CITY城市智能体前瞻 | 102 | 3批 | ~12min | 401,044 |
| 19.2026蓝皮书 | 200 | 6批 | ~24min | 493,375 |
| 5-刘默 推进可信数据空间 | 83 | 3批 | ~12min | 250,442 |
| **合计** | **975** | **30批** | **~2h** | **3,372,324** |

### 性能基准

- 30页/批：稳定在 600s 内完成（20~30页/页 × 0.8s + 0.5s间隔 ≈ 40s 纯API时间 + 传输延迟）
- 50页/批：部分PDF在 600s 内可完成，但中文内容多的页面（更长 API 返回）偶发超时
- 单页平均：~0.8s API 响应 + ~0.5s sleep = ~1.3s/页

### 限流处理

SiliconFlow 免费版有速率限制。`pdf_ocr.py` 内置：
- 每页 0.5s sleep 防 burst
- HTTP 429 自动等待 30s 后重试

## 环境要求

- `.env` 中配置 `SILICONFLOW_API_KEY`
- API Key 读取需用 `os.open()` 绕过 Hermes 凭证掩码
- PaddleOCR-VL-1.5 永久免费

## 性能参考

| 指标 | PaddleOCR-VL-1.5 | Qwen3-VL-8B (旧) | EasyOCR CPU |
|------|:---:|:---:|:---:|
| 单页速度 | **0.8s** | 2.4s | 77s |
| 费用 | **免费** | 收费 | 免费 |
| 准确率 | 95%+ | 95%+ | 90%+ |
| 30页总耗时 | ~40s | ~72s | ~38min |

**注意**：PaddleOCR 对培训照片/PPT 类扫描件可能输出乱码（韩文、LOC 标记等），需人工检查 OCR 质量。

## 常见超时原因及调整

| 问题 | 原因 | 对策 |
|------|------|------|
| 脚本 600s 超时 | 30页OCR内部分页面响应慢 | 改 `OCR_BATCH` 为 20 或 15 |
| subprocess 400s 超时 | 超大PDF 50页以上 | 减少每批页数，已改用 30页/批 |
| HTTP 429 | 免费版速率限制 | 脚本内置 30s 等待重试 |
| 中文引号文件名找不到 | 文件名含 `" "` 等特殊字符 | 用 `fitz.open(glob(...))` 或 Python glob 定位 |
| `fitz.open()`报错 | 系统python没有pymupdf | 用 `/opt/hermes/.venv/bin/python3` 运行 |

## 备选方案

如果 SiliconFlow 不可用，可切换至百炼：
- 模型: `qwen-vl-ocr` 或 `qwen3-vl-flash`
- 端点: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- 费用: ¥0.01/页
