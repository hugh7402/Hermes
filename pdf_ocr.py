"""
扫描件 PDF OCR — 通过 SiliconFlow PaddleOCR-VL-1.5 提取文字（免费，0.8s/页）
用法: python3 pdf_ocr.py <pdf_path> [start_page] [end_page]
- start_page: 起始页码（从0开始，默认0）
- end_page: 结束页码（不包含，默认全部）
示例: python3 pdf_ocr.py report.pdf 0 50   → OCR 第0~49页
"""
import sys, os, json, base64, urllib.request, time
from pathlib import Path

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "PaddlePaddle/PaddleOCR-VL-1.5"
MAX_OCR_PAGES = 99999  # 不再限制页数
OCR_BATCH_SIZE = 20  # 每批最多 OCR 20 页，防止超时

def get_api_key():
    fd = os.open("/opt/data/.env", os.O_RDONLY)
    try:
        data = os.read(fd, 8192).decode()
        for line in data.split('\n'):
            if line.startswith('SILICONFLOW_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    finally:
        os.close(fd)
    return None

def ocr_page(image_b64):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "请提取图片中所有文字，保持原文段落结构。只输出文字，不要加解释。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }],
        "max_tokens": 4000
    }).encode()

    api_key = get_api_key()
    req = urllib.request.Request(API_URL, data=payload)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

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
                print(f"✓ ({len(text)} 字)")
            except urllib.request.HTTPError as e:
                print(f"✗ HTTP {e.code}")
                if e.code == 429:
                    print(f"    ⏳ 触发限流，等待30秒后重试...")
                    time.sleep(30)
                    try:
                        text = ocr_page(img_b64)
                        pages_text.append(text)
                        print(f"    ✓ 重试成功 ({len(text)} 字)")
                        continue
                    except Exception as e2:
                        print(f"    ✗ 重试也失败: {e2}")
                pages_text.append(f"[第 {i+1} 页 OCR 失败: {e}]")
            except Exception as e:
                print(f"✗ {e}")
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
    
    if has_more:
        print(f"\n\n[⚠️ 已完成第1~{actual_end}页 OCR，共{total}页。继续运行: python3 pdf_ocr.py \"{filepath}\" {actual_end} {total}]")
