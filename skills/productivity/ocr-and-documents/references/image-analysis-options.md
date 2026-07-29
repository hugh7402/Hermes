# 图片分析与 OCR 方案汇总

在受限网络环境（GFW）下的图片/截图文字提取方案。

## 环境快速诊断

```bash
# 测试各 API 端点是否可达
for url in \
  "https://api.deepseek.com" \
  "https://dashscope.aliyuncs.com" \
  "https://api.siliconflow.cn" \
  "https://api.moonshot.cn" \
  "https://open.bigmodel.cn" \
  "https://generativelanguage.googleapis.com"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url" 2>/dev/null || echo "timeout")
  echo "$(echo $url | awk -F/ '{print $3}'): $code"
done
```

## 方案对比

| 方案 | 类型 | 安装/配置 | 适用场景 | 本环境状态 |
|------|------|-----------|----------|-----------|
| **SiliconFlow API** | 云端 | 免费注册→API Key | 通用图片理解、OCR | ✅ 可达，需配置 Key |
| **智谱 GLM-4V** | 云端 | 注册→API Key | 通用图片理解 | ✅ 可达，需配置 Key |
| **DashScope/百炼 (阿里)** | 云端 | 注册→API Key | Qwen-VL 视觉模型 | ✅ 可达，推荐！延迟最低 |
| **Google Gemini** | 云端 | API Key | 通用图片理解 | ❌ GFW 阻断 |
| **DeepSeek** | 云端 | API Key | 仅文本，不支持图片 | ❌ 模型不支持视觉 |
| **EasyOCR** | 本地 | `uv pip install easyocr` | 通用 OCR，中英文 | ⚠️ 首次安装需下载 ~2GB |
| **PaddleOCR** | 本地 | `uv pip install paddleocr` | 中文 OCR 最优 | ⚠️ 首次安装需下载 ~2GB |
| **Tesseract** | 本地 | `apt install tesseract-ocr` | 多语言 OCR | ❌ 需要 root 权限 |
| **ddddocr** | 本地 | `uv pip install ddddocr` | 验证码/短文本 | ⚠️ 仅支持短文本，不适合全页 OCR |
| **marker-pdf** | 本地 | `pip install marker-pdf` | PDF/扫描件 OCR | ⚠️ ~5GB，本技能已覆盖 |

## ddddocr 备忘

轻量级（~10MB），无需 PyTorch，安装秒级完成：

```bash
uv run --with ddddocr --with Pillow python3 -c "
import ddddocr
ocr = ddddocr.DdddOcr(show_ad=False, det=True)
with open('image.jpg', 'rb') as f:
    poses = ocr.detection(f.read())
print(f'检测到 {len(poses)} 个文字区域')
"
```

**限制**：`classification()` 只返回短字符串（适合验证码），`detection()` 能定位文字区域但无法可靠识别全页内容。不适合文档/截图 OCR。

## 推荐路径

1. **首选**：百炼直连（qwen-vl-max / qwen-vl-ocr，国内延迟最低）
2. **备选**：SiliconFlow 免费 API + Qwen3-VL-8B（配置 `SILICONFLOW_API_KEY` 到 `.env`）
3. **备选二**：智谱 GLM-4V
4. **本地**：`uv pip install easyocr`（一劳永逸但首次慢）

## 百炼视觉模型速查

| 模型 | 用途 | 推荐度 |
|------|------|:--:|
| `qwen-vl-max` | 通用图片/截图理解 | ⭐⭐⭐ |
| `qwen-vl-ocr` | 专注 OCR 文字提取 | ⭐⭐⭐ |
| `qwen3-vl-plus` | 新一代 VL 模型 | ⭐⭐ |

> 百炼视觉模型比 SiliconFlow 更快更稳（阿里直连），推荐作为图片识别主力。API 端点：`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`，Key 名：`BAILIAN_API_KEY`。

## SiliconFlow 实操脚本

```python
import subprocess, base64, json, urllib.request

# 读 Key
result = subprocess.run(['grep', 'SILICONFLOW_API_KEY', '/opt/data/.env'],
                       capture_output=True, text=True)
key = result.stdout.strip().split('=', 1)[1].strip().strip('"').strip("'")

# 读图片
with open('image.jpg', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

# 调用 Qwen3-VL-8B
payload = json.dumps({
    "model": "Qwen/Qwen3-VL-8B-Instruct",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "请详细描述这张图片，提取所有文字。用中文。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
        ]
    }],
    "max_tokens": 1500
}).encode()

req = urllib.request.Request('https://api.siliconflow.cn/v1/chat/completions', data=payload)
req.add_header('Authorization', f'Bearer {key}')
req.add_header('Content-Type', 'application/json')
resp = urllib.request.urlopen(req, timeout=60)
data = json.loads(resp.read())
print(data['choices'][0]['message']['content'])
```

### 已验证可用的模型

- `Qwen/Qwen3-VL-8B-Instruct` — 推荐，速度快，中文识别准确
- `Qwen/Qwen3-VL-32B-Instruct` — 质量更高但慢
- `PaddlePaddle/PaddleOCR-VL-1.5` — 专注 OCR

### 已禁用的模型（不要用）

- `Qwen/Qwen2-VL-72B-Instruct` — Model disabled
- `Pro/Qwen/Qwen2-VL-7B-Instruct` — Model disabled  
- `deepseek-ai/deepseek-vl2` — Model disabled
