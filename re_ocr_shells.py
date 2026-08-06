"""批量修复空壳文档 v2 — 本地 RapidOCR 版
- 对扫描件 PDF 强制 OCR 并覆盖写回 concepts/*.md
- 多进程并行（默认 4 workers，8 核 i3-N305）
- 断点续跑：跳过已完成的 md（>3000B）
用法: ocr_venv/bin/python3 re_ocr_shells.py [--workers N] [--only 关键词] [--limit N]
"""
import subprocess, sys, os, re, time, csv, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

BACKUP_DIR = "/opt/data/WebChat BackUp/文档"
CONCEPTS = "/opt/data/Obsidian Vault/Obsidian Vault/concepts"
OCR_VENV = "/opt/data/ocr_venv/bin/python3"
DONE_MARKER = "/tmp/re_ocr_done.json"  # 记录已完成的源文件

def norm(s):
    s = re.sub(r'^[\d一二三四五六七八九十百]+[\.、]?\s*', '', s)
    s = re.sub(r'[《》（）\[\]（）()\.\-_ ——-]', '', s)
    s = s.replace(' ', '')
    return s

def find_md(pdf_stem):
    key = norm(pdf_stem)
    for m in Path(CONCEPTS).glob('*.md'):
        if key == norm(m.stem):
            return m
    for m in Path(CONCEPTS).glob('*.md'):
        if key in norm(m.stem) or norm(m.stem) in key:
            return m
    return None

def ocr_pdf_local(pdf_path, max_pages=999):
    """本地 RapidOCR 逐页识别"""
    import fitz
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    pages_to_do = min(total, max_pages)
    texts = []
    for i in range(pages_to_do):
        img_path = None
        try:
            pix = doc[i].get_pixmap(dpi=100)
            img_path = f"/tmp/ocr_p{i}_{os.getpid()}.png"
            pix.save(img_path)
            result, _ = ocr(img_path)
            if result:
                page_text = "\n".join([line[1] for line in result])
                texts.append(f"\n\n---\n\n[第 {i+1}/{total} 页]\n\n{page_text}")
            else:
                texts.append(f"\n\n---\n\n[第 {i+1}/{total} 页 无文字]")
        except Exception as e:
            texts.append(f"\n\n---\n\n[第 {i+1}/{total} 页 OCR失败: {str(e)[:50]}]")
        finally:
            if img_path:
                try:
                    os.remove(img_path)
                except Exception:
                    pass
    doc.close()
    return "\n".join(texts), total

def process_one(item):
    """处理单个文件，返回 (status, name, pages, size)"""
    fname, pages_str, text_layer_str = item[0], item[1], item[2]
    pages = int(pages_str)
    text_layer = int(text_layer_str)
    pdf = Path(BACKUP_DIR) / fname
    if not pdf.exists():
        matches = list(Path(BACKUP_DIR).rglob(fname))
        if not matches:
            return ("SKIP", fname, pages, 0, "找不到源文件")
        pdf = matches[0]

    md = find_md(fname.replace('.pdf', ''))
    # 空壳判定：绝对 <3000B，或 每页不足150B（62页文档至少应9KB+）
    if md:
        sz = md.stat().st_size
        if sz >= 3000 and sz >= pages * 150:
            return ("SKIP", fname, pages, sz, "已完整")

    t0 = time.time()
    text, total = ocr_pdf_local(pdf)
    if not text.strip() or len(text.strip()) < 200:
        return ("FAIL", fname, pages, 0, f"识别内容过少({len(text.strip())}字)")

    if md is None:
        safe = fname.replace('.pdf', '') + '.md'
        md = Path(CONCEPTS) / safe
    content = f"# {md.stem}\n\n> **原始文件**：{fname}\n> **本地OCR重跑**：{time.strftime('%Y-%m-%d %H:%M')}（正文 {total} 页）\n\n---\n\n{text}\n"
    md.write_text(content, encoding='utf-8')
    return ("OK", fname, pages, md.stat().st_size, f"{time.time()-t0:.0f}s")

def load_done():
    if os.path.exists(DONE_MARKER):
        try:
            return set(json.load(open(DONE_MARKER)))
        except Exception:
            return set()
    return set()

def save_done(done_set):
    json.dump(sorted(done_set), open(DONE_MARKER, 'w'))

def main():
    args = sys.argv[1:]
    workers = 4
    only = None
    limit = None
    if '--workers' in args:
        workers = int(args[args.index('--workers')+1])
    if '--only' in args:
        only = args[args.index('--only')+1]
    if '--limit' in args:
        limit = int(args[args.index('--limit')+1])

    rows = list(csv.reader(open('/tmp/pdf_scan_report.csv')))
    suspects = [r for r in rows[1:] if r[5] == 'SUSPECT' and r[2] != '-1']
    # 本地处理小文件（<50页）+ 分担云端的中等文件（50-150页）
    suspects = [r for r in suspects if int(r[1]) < 150]
    if only:
        suspects = [r for r in suspects if only in r[0]]
    if limit:
        suspects = suspects[:limit]

    done = load_done()
    pending = [r for r in suspects if r[0] not in done]
    print(f"待处理: {len(pending)}/{len(suspects)} 个 (已完成 {len(suspects)-len(pending)})", flush=True)

    results = {"OK": 0, "FAIL": 0, "SKIP": 0}
    t_start = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(process_one, r): r for r in pending}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            try:
                status, fname, pages, size, note = fut.result()
                results[status] = results.get(status, 0) + 1
                if status == "OK":
                    done.add(r[0])
                    save_done(done)
                elapsed = time.time() - t_start
                print(f"[{i}/{len(pending)}] {status} {fname[:35]} | {pages}页 | md={size}B | {note} | 总耗时{elapsed/60:.0f}m", flush=True)
            except Exception as e:
                results["FAIL"] = results.get("FAIL", 0) + 1
                print(f"[{i}/{len(pending)}] EXC {r[0][:35]}: {str(e)[:80]}", flush=True)

    print(f"\n🎉 完成: OK={results['OK']} FAIL={results['FAIL']} SKIP={results['SKIP']} 总耗时{(time.time()-t_start)/60:.0f}分钟")

if __name__ == '__main__':
    main()
