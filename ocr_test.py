"""测试 RapidOCR 批量速度：连续 OCR 3 页计时"""
import time, sys
from rapidocr_onnxruntime import RapidOCR
import fitz

pdf = sys.argv[1] if len(sys.argv) > 1 else '/opt/data/WebChat BackUp/文档/20260731_上海市数据局发布可信数据空间建设运营指南附全文下载.pdf'
pages = [4, 7, 12]

ocr = RapidOCR()
doc = fitz.open(pdf)
for p in pages:
    pix = doc[p].get_pixmap(dpi=150)
    pix.save(f'/tmp/tp_{p}.png')
doc.close()

for p in pages:
    t0 = time.time()
    result, _ = ocr(f'/tmp/tp_{p}.png')
    dt = time.time() - t0
    text = '\n'.join([line[1] for line in result]) if result else ''
    print(f'第{p+1}页: {dt:.1f}s, {len(text)}字')
