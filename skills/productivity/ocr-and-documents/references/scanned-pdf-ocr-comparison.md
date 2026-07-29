# 中文扫描件 PDF OCR 方案实测对比

在无 GPU、CPU-only、无 root 的 Linux 环境下，对 46 份中文扫描件 PDF 的 OCR 方案对比。

## 环境约束

- CPU-only（无 GPU）
- 无 root 权限
- PEP 668 启用（需用 `uv run`）
- 百炼 API Key 已配置（`BAILIAN_API_KEY`）

## 方案对比

| | SiliconFlow Qwen3-VL-8B | 百炼 qwen-vl-ocr | EasyOCR CPU | PaddleOCR | marker-pdf |
|------|:--:|:--:|:--:|:--:|:--:|
| **类型** | 云端 API（免费） | 云端 API（付费） | 本地 PyTorch | 本地 Paddle | 本地 Surya |
| **安装大小** | 0 | 0 | ~700MB | ~400MB | ~4GB |
| **中文准确率** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **CPU 单页速度** | **~3s** | **~3s** | **~77s** ⚠️ | 兼容问题 | ~10-30s |
| **模型首次加载** | 0 | 0 | ~110s（仅一次） | — | ~30s |
| **9 页 PDF** | ~27s | ~27s | ~11min | — | ~2-4min |
| **44 页 PDF** | ~2min | ~2min | ~56min | — | ~8-15min |
| **46 份扫描件** | ~20min | ~20min | ~8h 😱 | — | — |
| **成本** | **¥0**（免费额度） | ≈¥0.01/页 | ¥0 | ¥0 | ¥0 |
| **本环境实测** | ✅ 可用 | ✅ 可用 | ✅ 可用但太慢 | ❌ NotImplementedError | 未测 |

## PaddleOCR 兼容问题

在 Python 3.13 + CPU-only 环境中，PaddleOCR (paddlepaddle 3.x) 报错：

```
NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]
```

这是 PaddlePaddle CPU 版本在特定 CPU 指令集上的兼容问题，非环境配置错误。

## EasyOCR 实测

**安装依赖（CPU-only，避免 2GB+ GPU 版本）：**

```bash
# 1. 先装 CPU 版 PyTorch（~183MB，不要从 PyPI 装会拉 GPU 版 ~2.5GB）
uv pip install --index-url https://download.pytorch.org/whl/cpu torch

# 2. 必须也从 CPU 索引装 torchvision，否则版本不匹配报错：
#   RuntimeError: operator torchvision::nms does not exist
uv pip install --reinstall --index-url https://download.pytorch.org/whl/cpu torchvision

# 3. 装 EasyOCR
uv pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple easyocr
```

> ⚠️ **关键陷阱**：PyPI 上的 torchvision 与 PyTorch CPU 版的 torch 不兼容。必须两者都从 `https://download.pytorch.org/whl/cpu` 安装。否则 `import easyocr` 时直接崩溃。

**OCR 调用：**

```bash
/opt/hermes/.venv/bin/python3 -c "
import easyocr, fitz

# 首次运行会下载检测/识别模型到 ~/.EasyOCR/ (~100MB)
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)  # 模型加载 ~110s（仅首次）

doc = fitz.open('scanned.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=200)
pix.save('/tmp/page.png')
result = reader.readtext('/tmp/page.png')  # ~77s/页（CPU）
for _, text, conf in result:
    print(text)
"
```

**速度参考（实测：无 GPU，200 dpi，1240×1753 页面）：**

| 阶段 | 耗时 |
|------|------|
| 模型首次下载 | ~100MB 下载（一次） |
| 模型加载（首次） | ~110s |
| 模型加载（缓存后） | ~5s |
| 单页 OCR | **~77s** |
| 9 页 PDF 全量 | ~11 min |
| 44 页 PDF 全量 | ~56 min |

> ⚠️ **EasyOCR CPU 不适配批量扫描件场景。** 比 SiliconFlow API 慢 25 倍。批处理 46 份扫描件需要 ~8 小时。仅适合零散的 1-2 页离线 OCR。

## 百炼 qwen-vl-ocr 实测

```python
# 已有 BAILIAN_API_KEY，直接调用
# 流程：PDF 页 → pymupdf 截图(200dpi) → base64 → API
# 端点：https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
# 模型：qwen-vl-ocr（专注 OCR，比 qwen-vl-max 更便宜）
```

优势：
- 零本地安装，即开即用
- 中英文 + 表格识别效果最好
- 46 页 ≈ ¥0.5

## 推荐策略

**批处理扫描件 PDF 的唯一可行方案：SiliconFlow API。**

决策树：

```
扫描件 PDF？
├── 是，有网络 → SiliconFlow Qwen3-VL-8B（免费，~3s/页）
├── 是，无网络 → EasyOCR CPU（~77s/页，仅零星用）
└── 非扫描件 → pymupdf（瞬间提取）
```

**为什么不用 EasyOCR 做批量：**
- CPU 推理 77s/页，44 页 = 56 分钟，46 份 = 8 小时
- API 同样是免费方案，快 25 倍
- 唯一何时用 EasyOCR：完全离线环境 + 仅 1-2 页

**为什么不用百炼 qwen-vl-ocr：**
- 免费额度用完后需付费（≈¥0.01/页）
- SiliconFlow 免费额度目前不限制视觉模型调用
- 准确率差异不大（95%+ vs 98%+，对入库场景都可接受）
