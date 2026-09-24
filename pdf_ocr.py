"""
扫描件 PDF OCR — 百炼 qwen-vl-ocr 为主（硅基流动 PaddleOCR-VL 为备用）
用法: python3 pdf_ocr.py <pdf_path> [start_page] [end_page]
- start_page: 起始页码（从0开始，默认0）
- end_page: 结束页码（不包含，默认全部）
示例: python3 pdf_ocr.py report.pdf 0 50   → OCR 第0~49页
"""
import sys, os, json, base64, urllib.request, time
from pathlib import Path

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "PaddlePaddle/PaddleOCR-VL-1.5"
# 引擎优先级：百炼(阿里云 DashScope)为主 —— 硅基流动账户 2026-09 起余额不足(402)，用户决定不充值；
# 硅基流动保留为备用，将来充值后会自动可用。
BAILIAN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
BAILIAN_MODEL = "qwen-vl-ocr-latest"
_ENGINE_ORDER = ["bailian", "siliconflow"]
_ENGINE = [_ENGINE_ORDER[0]]
MAX_OCR_PAGES = 99999  # 不再限制页数
OCR_BATCH_SIZE = 20  # 每批最多 OCR 20 页，防止超时

def _env_key(name):
    fd = os.open("/opt/data/.env", os.O_RDONLY)
    try:
        data = os.read(fd, 65536).decode()
        for line in data.split('\n'):
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    finally:
        os.close(fd)
    return None

def _post(url, model, prompt, image_b64, key, max_tokens=4000, timeout=120):
    payload = json.dumps({
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }],
        "max_tokens": max_tokens
    }).encode()
    req = urllib.request.Request(url, data=payload)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=timeout)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

def ocr_page_bailian(image_b64):
    key = _env_key("BAILIAN_API_KEY")
    if not key:
        raise RuntimeError("BAILIAN_API_KEY 未配置")
    return _post(BAILIAN_URL, BAILIAN_MODEL,
                 "请提取图片中所有文字，保持原文段落结构。只输出文字，不要加解释。",
                 image_b64, key)

def ocr_page_siliconflow(image_b64):
    key = _env_key("SILICONFLOW_API_KEY")
    if not key:
        raise RuntimeError("SILICONFLOW_API_KEY 未配置")
    return _post(API_URL, MODEL,
                 "请提取图片中所有文字，保持原文段落结构。只输出文字，不要加解释。",
                 image_b64, key)

def ocr_page(image_b64):
    """OCR 单页：百炼 qwen-vl-ocr 为主，失败自动回退硅基流动 PaddleOCR-VL。"""
    engine = _ENGINE[0]
    fn = ocr_page_bailian if engine == "bailian" else ocr_page_siliconflow
    alt = ocr_page_siliconflow if engine == "bailian" else ocr_page_bailian
    alt_name = "硅基流动" if engine == "bailian" else "百炼"
    try:
        return fn(image_b64)
    except Exception as e:
        code = getattr(e, "code", None)
        # 429 限流交给上层重试；其余（402 余额不足/网络/服务端错误）直接切备用引擎
        if code == 429:
            raise
        _ENGINE[0] = "siliconflow" if engine == "bailian" else "bailian"
        print(f"  ↩️ {engine} 不可用({code or type(e).__name__})，切换 {alt_name}", flush=True)
        return alt(image_b64)

def ocr_pdf_pages(filepath, start=0, end=None):
    """OCR 指定页码范围，返回 (text, total_pages, has_more, actual_end)"""
    import fitz
    doc = fitz.open(filepath)
    
    # Handle encrypted PDFs
    if doc.needs_pass:
        if not doc.authenticate(""):
            print(f"  🔒 加密PDF无法解密，尝试空密码失败")
            doc.close()
            doc = fitz.open(filepath)
            doc.authenticate("")

    total = len(doc)
    if end is None or end > total:
        end = total
    
    all_text = []
    current_start = start
    ok_pages = 0
    fail_pages = 0
    
    while current_start < end:
        # 限制每批最大 OCR_BATCH_SIZE 页
        batch_end = min(current_start + OCR_BATCH_SIZE, end)
        if batch_end <= current_start:
            batch_end = min(current_start + OCR_BATCH_SIZE, total)
        
        pages_to_ocr = batch_end - current_start
        print(f"  📸 OCR 第{current_start+1}~{batch_end}页 ({pages_to_ocr}/{total} 页)")
        
        pages_text = []
        for i in range(current_start, batch_end):
            try:
                page = doc[i]
            except ValueError as e:
                print(f"    第 {i+1} 页无法加载: {e}")
                pages_text.append(f"[第 {i+1} 页：加密保护，无法提取]")
                continue
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode()
            
            print(f"    第 {i+1}/{total} 页...", end=" ", flush=True)
            try:
                text = ocr_page(img_b64)
                pages_text.append(text)
                ok_pages += 1
                print(f"✓ ({len(text)} 字)")
            except urllib.request.HTTPError as e:
                print(f"✗ HTTP {e.code}")
                fail_pages += 1
                if e.code == 429:
                    print(f"    ⏳ 触发限流，等待30秒后重试...")
                    time.sleep(30)
                    try:
                        text = ocr_page(img_b64)
                        pages_text.append(text)
                        ok_pages += 1
                        print(f"    ✓ 重试成功 ({len(text)} 字)")
                        continue
                    except Exception as e2:
                        print(f"    ✗ 重试也失败: {e2}")
                pages_text.append(f"[第 {i+1} 页 OCR 失败: {e}]")
            except Exception as e:
                print(f"✗ {e}")
                fail_pages += 1
                pages_text.append(f"[第 {i+1} 页 OCR 失败]")
            
            time.sleep(0.5)
        
        if pages_text:
            all_text.append("\n\n---\n\n".join(pages_text))
        
        current_start = batch_end
        
        # 如果还有下一页要处理，加一条分隔提示
        if current_start < end:
            print(f"  📄 已完成第1~{current_start}页，继续处理剩余{end-current_start}页...")
    
    doc.close()
    
    has_more = False  # 内部已全部处理完
    text = "\n\n---\n\n".join(all_text)
    actual_end = end

    globals()["LAST_OCR_STATS"] = (ok_pages, fail_pages)

    return text, total, has_more, actual_end


def ocr_pdf_old(filepath):
    """旧版——全量 OCR（兼容调用）"""
    return ocr_pdf_pages(filepath, 0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 pdf_ocr.py <pdf_path> [start_page] [end_page]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    text, total, has_more, actual_end = ocr_pdf_pages(filepath, start, end)
    print(text)

    ok_pages, fail_pages = globals().get("LAST_OCR_STATS", (0, 0))
    if ok_pages == 0 and fail_pages > 0:
        sys.stderr.write(f"\n[OCR 全部失败] {fail_pages}/{total} 页均失败（常见原因：API 402 余额不足 / 429 限流 / 网络）\n")
        sys.exit(2)
    
    if has_more:
        print(f"\n\n[⚠️ 已完成第1~{actual_end}页 OCR，共{total}页。继续运行: python3 pdf_ocr.py \"{filepath}\" {actual_end} {total}]")
