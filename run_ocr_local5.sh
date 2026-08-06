#!/bin/bash
# OCR 本地引擎 wrapper
cd /opt/data
/opt/data/ocr_venv/bin/python3 /opt/data/re_ocr_shells.py --workers 2 > /tmp/re_ocr_local5.log 2>&1
