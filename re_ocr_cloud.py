"""云端 OCR 批量修复（硅基流动 PaddleOCR-VL）— 并行处理大文件
用法: ocr_venv/bin/python3 re_ocr_cloud.py --workers 2 [--limit N]
- 默认只处理 >=50 页的大文件（小文件交给本地 re_ocr_shells.py）
- 逐页渲染 100dpi → 调 PaddleOCR-VL → 写回 concepts/*.md
- 断点：跳过已写 done 标记的文件
"""
import base64, json, os, re, sys, time, csv, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BACKUP_DIR = "/opt/data/WebChat BackUp/文档"
CONCEPTS = "/opt/data/Obsidian Vault/Obsidian Vault/concepts"
DONE_MARKER = "/tmp/re_ocr_cloud_done.json"
MIN_PAGES = 50  # 云端处理 50+ 页文件（2026-08-04 用户要求分流：本地RapidOCR忙不过来，50页以上给云端PaddleOCR-VL加速）

def get_key():
    fd = os.open('/opt/data/.env', os.O_RDONLY)
    data = os.read(fd, 100000).decode()
    os.close(fd)
    for line in data.splitlines():
        if line.startswith('SILICONFLOW_API_KEY='):
            return line.split('=', 1)[1].strip()
    raise RuntimeError("no key")

KEY = get_key()

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

def ocr_page_vlm(pdf_path, page_idx, total):
    """渲染单页并调 PaddleOCR-VL"""
    import fitz
    doc = fitz.open(str(pdf_path))
    pix = doc[page_idx].get_pixmap(dpi=100)
    png = f"/tmp/cloud_p{page_idx}_{os.getpid()}.png"
    pix.save(png)
    doc.close()
    try:
        img_b64 = base64.b64encode(open(png, 'rb').read()).decode()
        payload = {
            "model": "PaddlePaddle/PaddleOCR-VL-1.5",
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": "识别图片中所有文字，按阅读顺序输出，保留段落结构。不要输出任何解释。"}
            ]}],
            "max_tokens": 2000
        }
        proxy = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'})
        opener = urllib.request.build_opener(proxy)
        req = urllib.request.Request(
            "https://api.siliconflow.cn/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
        )
        for attempt in range(3):
            try:
                resp = opener.open(req, timeout=120)
                d = json.loads(resp.read())
                return d['choices'][0]['message']['content']
            except Exception as e:
                if attempt == 2:
                    return f"[第{page_idx+1}页 OCR失败: {str(e)[:80]}]"
                time.sleep(5)
    finally:
        try:
            os.remove(png)
        except Exception:
            pass

def process_one(item):
    fname, pages_str = item[0], item[1]
    pages = int(pages_str)
    pdf = Path(BACKUP_DIR) / fname
    if not pdf.exists():
        matches = list(Path(BACKUP_DIR).rglob(fname))
        if not matches:
            return ("SKIP", fname, pages, 0, "找不到源文件")
        pdf = matches[0]

    md = find_md(fname.replace('.pdf', ''))
    if md:
        sz = md.stat().st_size
        if sz >= 3000 and sz >= pages * 150:
            return ("SKIP", fname, pages, sz, "已完整")

    t0 = time.time()
    import fitz
    doc = fitz.open(str(pdf))
    total = doc.page_count
    doc.close()
    texts = []
    for i in range(total):
        t = ocr_page_vlm(pdf, i, total)
        texts.append(f"\n\n---\n\n[第 {i+1}/{total} 页]\n\n{t}")
        if (i + 1) % 10 == 0:
            print(f"    {fname[:30]}... {i+1}/{total}页 ({time.time()-t0:.0f}s)", flush=True)

    text = "\n".join(texts)
    if len(text.strip()) < 200:
        return ("FAIL", fname, pages, 0, f"识别内容过少({len(text.strip())}字)")

    if md is None:
        safe = fname.replace('.pdf', '') + '.md'
        md = Path(CONCEPTS) / safe
    content = f"# {md.stem}\n\n> **原始文件**：{fname}\n> **云端OCR(PaddleOCR-VL)重跑**：{time.strftime('%Y-%m-%d %H:%M')}（正文 {total} 页）\n\n---\n\n{text}\n"
    md.write_text(content, encoding='utf-8')
    return ("OK", fname, pages, md.stat().st_size, f"{time.time()-t0:.0f}s")

def main():
    args = sys.argv[1:]
    workers = 2
    limit = None
    if '--workers' in args:
        workers = int(args[args.index('--workers')+1])
    if '--limit' in args:
        limit = int(args[args.index('--limit')+1])

    rows = list(csv.reader(open('/tmp/pdf_scan_report.csv')))
    suspects = [r for r in rows[1:] if r[5] == 'SUSPECT' and r[2] != '-1']

    # 云端只处理大文件（>=MIN_PAGES 页），小文件交给本地脚本
    suspects = [r for r in suspects if int(r[1]) >= MIN_PAGES]

    # 本地断点 + 云端断点合并
    done_local = set()
    if os.path.exists("/tmp/re_ocr_done.json"):
        done_local = set(json.load(open("/tmp/re_ocr_done.json")))
    done_cloud = set()
    if os.path.exists(DONE_MARKER):
        done_cloud = set(json.load(open(DONE_MARKER)))
    done = done_local | done_cloud

    pending = [r for r in suspects if r[0] not in done]
    if limit:
        pending = pending[:limit]
    print(f"待处理: {len(pending)} 个", flush=True)

    results = {"OK": 0, "FAIL": 0, "SKIP": 0}
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(process_one, r): r for r in pending}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            try:
                status, fname, pages, size, note = fut.result()
                results[status] = results.get(status, 0) + 1
                if status == "OK":
                    done_cloud.add(r[0])
                    json.dump(sorted(done_cloud), open(DONE_MARKER, 'w'))
                elapsed = time.time() - t_start
                print(f"[{i}/{len(pending)}] {status} {fname[:35]} | {pages}页 | md={size}B | {note} | 总耗时{elapsed/60:.0f}m", flush=True)
            except Exception as e:
                results["FAIL"] = results.get("FAIL", 0) + 1
                print(f"[{i}/{len(pending)}] EXC {r[0][:35]}: {str(e)[:80]}", flush=True)

    print(f"\n🎉 云端OCR完成: OK={results['OK']} FAIL={results['FAIL']} SKIP={results['SKIP']} 总耗时{(time.time()-t_start)/60:.0f}分钟")

if __name__ == '__main__':
    main()
