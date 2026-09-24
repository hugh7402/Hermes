#!/usr/bin/env python3
"""
百炼(DashScope) OCR 入库 —— 硅基流动欠费/不可用时的主力引擎。

用法: python3 bailian_ocr_ingest.py <pdf_path> [start_page]

特性:
- 逐页 OCR，结果缓存到 ocr_cache_<md5>.json，每 5 页刷盘 → 中断可断点续传
- 输出 md 到 Obsidian concepts/（[第 N/M 页] 分隔），并调 note_enhance 加 frontmatter
- 追加 pdf md5 到 .ingested，打印 token 用量与预估费用

注意:
- 必须用 /opt/data/ocr_venv/bin/python3 跑（需要 fitz / PIL）
- 模型用 qwen-vl-ocr-latest（0.3/0.5 元每百万 tok）；旧快照 -2025-08-28 等是 5 元，贵 16 倍
- 实测 ≈5-6.6s/页；31 页约 3 分钟、204 页约 18-20 分钟
"""
import sys, os, json, base64, hashlib, time, urllib.request, urllib.error
from pathlib import Path

ENV = "/opt/data/.env"
VAULT = Path("/opt/data/Obsidian Vault/Obsidian Vault")
CONCEPTS = VAULT / "concepts"
PROCESSED = VAULT / ".ingested"
CACHE_DIR = Path("/opt/data/.tmp_tests")
MODELS = ["qwen-vl-ocr-latest", "qwen-vl-ocr", "qwen-vl-max-latest"]
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
PROMPT = "请提取这张图片中的所有文字，保持原有的段落顺序和结构。只输出文字内容，不要添加任何解释。"
# 官方原价（华北2 北京）：输入 0.3 元/百万tok，输出 0.5 元/百万tok
PRICE_IN, PRICE_OUT = 0.3, 0.5


def get_key(name):
    fd = os.open(ENV, os.O_RDONLY)
    d = os.read(fd, 65536).decode()
    os.close(fd)
    for l in d.splitlines():
        l = l.strip()
        if l.startswith(name + "="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


KEY = get_key("BAILIAN_API_KEY")


def ocr_image(png_bytes, model):
    b64 = base64.b64encode(png_bytes).decode()
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
            {"type": "text", "text": PROMPT},
        ]}],
        "max_tokens": 4000,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    txt = (r["choices"][0]["message"].get("content") or "").strip()
    u = r.get("usage", {}) or {}
    return txt, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def main():
    pdf = Path(sys.argv[1])
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    h = hashlib.md5(pdf.read_bytes()).hexdigest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_f = CACHE_DIR / f"ocr_cache_{h}.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}

    import fitz
    doc = fitz.open(str(pdf))
    total = len(doc)
    print(f"[{pdf.stem}] {total} 页, 缓存已有 {len(cache)} 页", flush=True)

    model = MODELS[0]
    in_tok = out_tok = ok = 0
    t0 = time.time()

    for i in range(start, total):
        k = str(i)
        if k in cache and cache[k].strip():
            ok += 1
            continue
        try:
            png = doc[i].get_pixmap(dpi=200).tobytes("png")
        except Exception as e:
            cache[k] = f"[第 {i+1} 页渲染失败: {e}]"
            continue

        for attempt in range(3):
            try:
                txt, ti, to = ocr_image(png, model)
                cache[k] = txt
                in_tok += ti
                out_tok += to
                ok += 1
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:120]
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                if model != MODELS[-1] and ("model" in body.lower() or e.code == 404):
                    model = MODELS[MODELS.index(model) + 1]
                    print(f"  ↩️ 切换模型 → {model}", flush=True)
                    continue
                cache[k] = f"[第 {i+1} 页 OCR 失败: HTTP {e.code} {body}]"
                break
            except Exception as e:
                if attempt == 2:
                    cache[k] = f"[第 {i+1} 页 OCR 失败: {str(e)[:80]}]"
                else:
                    time.sleep(3)
        if (i + 1) % 5 == 0 or i == total - 1:
            cache_f.write_text(json.dumps(cache, ensure_ascii=False))
            el = time.time() - t0
            print(f"  {i+1}/{total} 页  ({el:.0f}s, {el/max(i+1-start,1):.1f}s/页, "
                  f"tok in/out={in_tok}/{out_tok})", flush=True)
        time.sleep(0.15)

    doc.close()
    cache_f.write_text(json.dumps(cache, ensure_ascii=False))

    parts = [f"# {pdf.stem}", "",
             f"> **原始文件**：{pdf.name}",
             f"> **OCR 引擎**：百炼 {model}（正文 {total} 页）", "---", ""]
    total_chars = 0
    for i in range(total):
        t = cache.get(str(i), "")
        total_chars += len(t)
        parts += [f"[第 {i+1}/{total} 页]", "", t, "", "---", ""]
    md_path = CONCEPTS / f"{pdf.stem}.md"
    md_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"✅ 写入 {md_path}  ({total_chars} 字)", flush=True)

    # 用 subprocess 列表参数（不用 os.system，避免 shell 注入）
    import subprocess
    rc = subprocess.run(["/opt/data/.venv/bin/python3", "/opt/data/note_enhance.py", md_path.name],
                        cwd="/opt/data", capture_output=True).returncode
    print(f"note_enhance rc={rc}", flush=True)

    with open(PROCESSED, "a") as f:
        f.write(h + "\n")

    cost = in_tok / 1_000_000 * PRICE_IN + out_tok / 1_000_000 * PRICE_OUT
    print(f"SUMMARY|{pdf.stem}|pages={total}|ok={ok}|chars={total_chars}"
          f"|in_tok={in_tok}|out_tok={out_tok}|cost_yuan≈{cost:.4f}")


if __name__ == "__main__":
    main()
