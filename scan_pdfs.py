"""扫描所有 PDF，检测"文字版误判"：页数多但文字少 / 大量图片页无文字层"""
import os, sys, json, csv
from pathlib import Path

try:
    import fitz
except ImportError:
    print("NEED_PYMUPDF")
    sys.exit(2)

BACKUP_DIR = "/opt/data/WebChat BackUp/文档"
OUT = "/tmp/pdf_scan_report.csv"

rows = []
pdfs = sorted(Path(BACKUP_DIR).rglob("*.pdf"))
for p in pdfs:
    try:
        doc = fitz.open(str(p))
        pages = doc.page_count
        total_text = 0
        img_pages = 0
        text_pages = 0
        for i in range(pages):
            t = doc[i].get_text().strip()
            n = len(t)
            total_text += n
            if n > 0:
                text_pages += 1
            if doc[i].get_images():
                img_pages += 1
        doc.close()
        # 判定: 文字总量 < 800 或 有图片页且文字页占比低
        flag = ""
        if pages >= 3 and (total_text < 800 or (img_pages > 0 and text_pages / pages < 0.5)):
            flag = "SUSPECT"
        elif pages >= 1 and total_text < 50:
            flag = "EMPTY"
        rows.append([p.name, pages, total_text, text_pages, img_pages, flag])
    except Exception as e:
        rows.append([p.name, -1, -1, -1, -1, f"ERR:{str(e)[:30]}"])

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["file", "pages", "text_chars", "text_pages", "img_pages", "flag"])
    w.writerows(rows)

suspects = [r for r in rows if r[5] == "SUSPECT"]
empties = [r for r in rows if r[5] == "EMPTY"]
print(f"TOTAL={len(rows)} SUSPECT={len(suspects)} EMPTY={len(empties)}")
for r in suspects[:40]:
    print(f"SUSPECT|{r[0]}|pages={r[1]}|text={r[2]}|textpages={r[3]}|imgpages={r[4]}")
for r in empties[:20]:
    print(f"EMPTY|{r[0]}|pages={r[1]}|text={r[2]}|textpages={r[3]}|imgpages={r[4]}")
