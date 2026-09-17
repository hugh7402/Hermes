"""OCR 检查 B站米兰纪录片帧内硬字幕（rapidocr_onnxruntime 旧版 API）"""
import glob
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
for p in sorted(glob.glob('/tmp/milan_frames/*.jpg')):
    name = p.split('/')[-1]
    try:
        result, _ = engine(p)
        texts = [r[1] for r in result] if result else []
        if texts:
            print(f'{name}: {" | ".join(texts)[:220]}')
        else:
            print(f'{name}: (无文字)')
    except Exception as e:
        print(f'{name}: OCR异常 {str(e)[:80]}')
