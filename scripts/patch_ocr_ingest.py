#!/opt/data/ocr_venv/bin/python
"""
扫描件 PDF 补入库 worker —— 由 retry_pdf_ingest.sh (cron) 调用。

设计原则：
- SiliconFlow OCR 不可用（402 余额不足/网络）→ 不输出任何 stdout，完全静默；只写 /tmp 日志。
- 可用时才对目标扫描件做 OCR，校验通过才写 md 入库；全部完成写 done 标记。
- OCR 输出质量门：成功页字数 >= 页数*50，且失败页占比 < 40%，否则判失败不写库（避免污染知识库）。
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

def _pick_dir(*cands):
    """目录名历史上出现过带/不带空格的两种拼法，取实际存在的。"""
    for c in cands:
        if Path(c).is_dir():
            return Path(c)
    return Path(cands[0])


DOC = _pick_dir("/opt/data/WebChat BackUp/文档", "/opt/data/WebChat Back Up/文档")
VAULT = Path("/opt/data/Obsidian Vault/Obsidian Vault")
CONCEPTS = VAULT / "concepts"
PROCESSED = VAULT / ".ingested"
LOG = Path("/tmp/retry_pdf_ingest.log")
DONE_MARK = Path("/opt/data/scripts/.pdf_ingest_retry_done")
LOCK = Path("/tmp/retry_pdf_ingest.lock")
OCR_PY = "/opt/data/pdf_ocr.py"
OCR_PYTHON = "/opt/data/ocr_venv/bin/python3"
MODEL = "PaddlePaddle/PaddleOCR-VL-1.5"

TARGETS = [
    "4.《2026年中国Token经济产业研究》.pdf",
    "5.马清泉团队《Token经济100问》.pdf",
    "6.《2026年中国Token工厂发展白皮书》.pdf",
]


def log(msg):
    with LOG.open("a") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


def api_key():
    for line in Path("/opt/data/.env").read_text().splitlines():
        if line.startswith("SILICONFLOW_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def bailian_key():
    for line in Path("/opt/data/.env").read_text().splitlines():
        if line.startswith("BAILIAN_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _probe_png():
    """探针图片：qwen-vl-ocr 有最小尺寸限制，1x1 会被拒，故用 200x100 白图。"""
    try:
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (200, 100), "white").save(buf, format="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )


def _probe(url, model, key):
    png = _probe_png()
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "OK"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}},
        ]}],
        "max_tokens": 10,
    }).encode()
    req = urllib.request.Request(url, data=payload)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=25)
        return True, "OK"
    except Exception as exc:  # noqa: BLE001
        body = ""
        if hasattr(exc, "read"):
            try:
                body = exc.read().decode()[:160]
            except Exception:  # noqa: BLE001
                pass
        return False, f"{exc} {body}"


def ocr_available():
    """端到端探针：硅基流动优先，不可用则测百炼 qwen-vl-ocr 兜底。"""
    ok, detail = _probe("https://api.siliconflow.cn/v1/chat/completions",
                        MODEL, api_key())
    if ok:
        return True, "OK (SiliconFlow)"
    b_ok, b_detail = _probe(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "qwen-vl-ocr-latest", bailian_key())
    if b_ok:
        return True, "OK (百炼兜底)"
    return False, f"SiliconFlow: {detail} | 百炼: {b_detail}"


def pdf_pages(path):
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            return len(doc)
    except Exception:  # noqa: BLE001
        return 0


def md_ok(md_path, pages):
    """已有 md 是否合格（防止把 402 空壳当成果）。"""
    if not md_path.exists():
        return False
    txt = md_path.read_text(errors="ignore")
    if "HTTP 402" in txt or "余额不足" in txt:
        return False
    if pages and len(txt) < max(3000, pages * 120):
        return False
    return len(txt) >= 3000


def mark_processed(pdf_path):
    h = hashlib.md5(pdf_path.read_bytes()).hexdigest()
    existing = PROCESSED.read_text().splitlines() if PROCESSED.exists() else []
    if h not in existing:
        with PROCESSED.open("a") as fh:
            fh.write(h + "\n")


def main():
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3600:
        log("上次运行仍在进行，跳过本轮")
        return 0
    LOCK.write_text(str(os.getpid()))

    try:
        if DONE_MARK.exists():
            return 0

        ok, detail = ocr_available()
        log(f"SiliconFlow 探针: {'OK' if ok else 'DOWN: ' + detail}")
        if not ok:
            return 0  # 静默：等余额恢复

        results = []
        pending = 0
        for name in TARGETS:
            pdf = DOC / name
            if not pdf.exists():
                continue
            base = name[:-4]
            md = CONCEPTS / f"{base}.md"
            pages = pdf_pages(pdf)
            if md_ok(md, pages):
                continue
            pending += 1
            log(f"OCR 开始 {base}（{pages}页）")
            out_txt = Path(f"/tmp/ocr_{hashlib.md5(name.encode()).hexdigest()[:8]}.txt")
            try:
                proc = subprocess.run(
                    [OCR_PYTHON, OCR_PY, str(pdf)],
                    capture_output=True, text=True, timeout=2400,
                )
            except subprocess.TimeoutExpired:
                log(f"OCR 超时(>40min) {base}")
                results.append(f"⏰ {base}：OCR 超时未完成（{pages}页扫描件，需单独跑）")
                continue

            text = proc.stdout
            # 去掉进度行（含 📸/第 N 页 的日志行）后再校验正文量
            body = "\n".join(l for l in text.splitlines()
                             if not l.strip().startswith(("📸", "📄", "第 ", "   第")))
            failed = text.count("页 OCR 失败")
            need = max(3000, pages * 50)
            if proc.returncode != 0 or len(body) < need or (pages and failed > pages * 0.4):
                reason = (proc.stderr.strip().splitlines() or ["未知"])[-1] if proc.stderr.strip() else f"正文仅{len(body)}字/需{need}字"
                log(f"OCR 失败 {base}: rc={proc.returncode} {reason}")
                results.append(f"❌ {base}：OCR 失败 — {reason[:120]}")
                continue

            out_txt.write_text(body)
            md_content = f"# {base}\n\n> **原始文件**：{name}\n\n---\n\n" + body.replace("\n# ", "\n## ")
            md.write_text(md_content)
            subprocess.run(["/opt/data/ocr_venv/bin/python3", "/opt/data/note_enhance.py", md.name],
                           cwd=str(CONCEPTS), timeout=600, capture_output=True)
            mark_processed(pdf)
            log(f"✅ 入库 {base}（{len(body)}字）")
            results.append(f"✅ {base}：OCR {pages} 页入库（{len(body)}字）")

        if not results:
            return 0

        left = 0
        for name in TARGETS:
            pdf = DOC / name
            if pdf.exists():
                md = CONCEPTS / f"{name[:-4]}.md"
                if not md_ok(md, pdf_pages(pdf)):
                    left += 1
        if left == 0:
            DONE_MARK.write_text(time.strftime("%Y-%m-%d %H:%M"))
            results.append("🎉 3 个 Token 扫描件已全部补入库，本重试任务结束")
        print("📚 扫描件补入库（SiliconFlow OCR 已恢复）")
        print("\n".join(results))
        return 0
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
