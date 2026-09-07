#!/usr/bin/env python3
"""OCR 知无涯者抽帧，检测是否硬字幕（中文字幕烧录进画面）"""
import os, sys, glob

# 用本地 RapidOCR（ocr_venv）或 OCR API
os.environ['PATH'] = '/opt/data/ocr_venv/bin:' + os.environ['PATH']
os.environ['VIRTUAL_ENV'] = '/opt/data/ocr_venv'

try:
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
except Exception as e:
    print(f'RapidOCR 不可用: {e}')
    sys.exit(2)

for jpg in sorted(glob.glob('/tmp/zwnz_frames/*.jpg')):
    result, _ = engine(jpg)
    if result:
        texts = [line[1] for line in result]
        joined = ' | '.join(texts)
        print(f'{os.path.basename(jpg)}: {joined[:120]}')
    else:
        print(f'{os.path.basename(jpg)}: (无文字)')
