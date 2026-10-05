#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重 OCR 污染笔记：用百炼 qwen-vl-ocr 引擎重跑源 PDF，重建 md 正文

输入: /opt/data/.tmp_tests/reocr_plan.json（md → 源 PDF + 页数）
输出: 直接覆写 md（去掉旧的 frontmatter，让 note_enhance 重新生成）
断点续传: /opt/data/.tmp_tests/reocr_done.json
"""
import base64, json, os, re, sys, time, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, '/opt/data')
PLAN = '/opt/data/.tmp_tests/reocr_plan.json'
DONE = '/opt/data/.tmp_tests/reocr_done.json'
V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts/'
KEY = re.search(r'BAILIAN_API_KEY\s*=\s*["\']?([^"\'\n]+)', open('/opt/data/.env').read()).group(1)
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-vl-ocr-latest"
PROMPT = "请提取图片中所有文字，保持原文段落结构。只输出文字，不要加解释。"
WORKERS = 8
DPI = 150

_LOC = re.compile(r'<\|LOC_\d+\|>')
_lock = threading.Lock()
tok_total = [0]

def ocr_image(png_b64, page_no):
    """单页 OCR，429 退避重试"""
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{png_b64}"}}]}],
        "max_tokens": 6000}).encode()
    last = None
    for att in range(5):
        try:
            req = urllib.request.Request(URL, data=body,
                  headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=150).read())
            t = r['choices'][0]['message']['content'] or ''
            with _lock:
                tok_total[0] += r.get('usage', {}).get('total_tokens', 0)
            return _LOC.sub('', t).strip()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                time.sleep(6 * (att + 1))
            else:
                time.sleep(3)
        except Exception as e:
            last = e
            time.sleep(3)
    return f"[第 {page_no} 页 OCR 失败: {type(last).__name__}]"

def reocr_one(entry):
    """重 OCR 单个文件，返回 (file, status, pages_ok, pages_fail)"""
    import fitz
    md_path = os.path.join(V, entry['file'])
    src = entry['src']
    try:
        doc = fitz.open(src)
        n = len(doc)
        if doc.needs_pass:
            doc.authenticate("")
        # 逐页渲染（不一次性持有全部图片，控内存）
        imgs = []
        for i in range(n):
            pix = doc[i].get_pixmap(dpi=DPI)
            imgs.append(base64.b64encode(pix.tobytes("png")).decode())
            pix = None
        doc.close()
    except Exception as e:
        return entry['file'], f'open_fail:{type(e).__name__}', 0, 0

    texts = [None] * n
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(ocr_image, imgs[i], i + 1): i for i in range(n)}
        for f in as_completed(futs):
            i = futs[f]
            t = f.result()
            texts[i] = t
            if t.startswith('[第 ') and 'OCR 失败' in t:
                fail += 1
            else:
                ok += 1
    imgs = None

    # 取标题：优先现有 frontmatter title，其次 # H1，再次 PDF 名
    title = os.path.splitext(os.path.basename(src))[0]
    try:
        cur = open(md_path, encoding='utf-8', errors='ignore').read()
        m = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', cur, re.M)
        if m:
            title = m.group(1).strip()
        else:
            m2 = re.search(r'^#\s+(.+)$', cur, re.M)
            if m2:
                title = m2.group(1).strip()
    except Exception:
        pass

    body = '\n\n'.join(t for t in texts if t)
    header = (f"# {title}\n\n"
              f"> **原始文件**：{os.path.basename(src)}\n"
              f"> **云端OCR(qwen-vl-ocr)重跑**：{datetime.now():%Y-%m-%d %H:%M}（正文 {n} 页）\n"
              f"---\n\n")
    with open(md_path, 'w', encoding='utf-8') as fh:
        fh.write(header + body + '\n')
    return entry['file'], 'ok', ok, fail

def main():
    plan = json.load(open(PLAN))
    done = json.load(open(DONE)) if os.path.exists(DONE) else {}
    targets = [e for e in plan if e['src'] and e['pages'] > 0 and e['file'] not in done]
    print(f"计划 {len(plan)} 篇，有源 PDF {sum(1 for e in plan if e['src'])} 篇，"
          f"已完成 {len(done)}，待处理 {len(targets)}", flush=True)
    print(f"待处理总页数: {sum(e['pages'] for e in targets)}", flush=True)

    t0 = time.time()
    for i, e in enumerate(targets, 1):
        ts = time.time()
        f, st, ok, fail = reocr_one(e)
        el = time.time() - ts
        done[f] = {'status': st, 'ok': ok, 'fail': fail, 'pages': e['pages'],
                   'sec': round(el, 1)}
        json.dump(done, open(DONE, 'w'), ensure_ascii=False, indent=1)
        print(f"[{i}/{len(targets)}] {st:10s} {ok:4d}ok/{fail:3d}fail "
              f"{el:6.0f}s  {f[:56]}", flush=True)

    tot = time.time() - t0
    n_ok = sum(1 for v in done.values() if v['status'] == 'ok')
    print(f"\n{'='*66}")
    print(f"=== 重 OCR 完成: {n_ok}/{len(plan)} 篇成功 / 耗时 {tot/60:.1f} 分钟 "
          f"/ tokens={tok_total[0]} ≈ ¥{tok_total[0]/1e6*0.5:.2f} ===", flush=True)

if __name__ == '__main__':
    main()
