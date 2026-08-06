#!/bin/bash
# OCR 双引擎 wrapper
cd /opt/data
/opt/data/ocr_venv/bin/python3 /opt/data/re_ocr_cloud.py --workers 2 > /tmp/re_ocr_cloud5.log 2>&1
