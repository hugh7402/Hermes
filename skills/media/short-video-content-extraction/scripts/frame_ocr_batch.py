#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐帧 OCR 批处理 —— 从烧录字幕视频还原口播稿

用法:
    python3 frame_ocr_batch.py <帧目录> [--workers 6] [--out ocr.json]

前置: 先用 ffmpeg 抽帧
    ffmpeg -v error -i video.mp4 -vf fps=1 -q:v 2 all/f%04d.jpg -y

特性:
  - 百炼 qwen-vl-ocr-latest，prompt 固定用官方任务关键字 `Text Recognition:`
    （自由文本 prompt 会让模型吐 x1,y1,x2,y2,angle 坐标而不是文字——已在 skill 里记档）
  - 并发（默认 6；实测 6 够用，不必调到 12+）
  - 断点续传：每 20 帧落盘一次，重跑自动跳过已完成帧
  - 429 退避重试
  - 末尾输出 token 数与估算费用（用户明确要求汇报计量）

⚠️ 不要把这个脚本的输出接 `| head -N`——SIGPIPE 会杀掉它，末尾的 json.dump 不会执行。
   要截断就重定向到文件: python3 frame_ocr_batch.py all > log 2>&1
"""
import base64, glob, json, os, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BAILIAN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-vl-ocr-latest"
PROMPT = "Text Recognition:"          # ← 不要改。自由文本 prompt 会返回坐标元组
ENV = '/opt/data/.env'
LOC_RE = re.compile(r'<\|LOC_\d+\|>')  # PaddleOCR-VL 兜底引擎会吐布局 token


def api_key():
    m = re.search(r'BAILIAN_API_KEY\s*=\s*["\']?([^"\'\n]+)', open(ENV).read())
    if not m:
        raise RuntimeError('BAILIAN_API_KEY 未在 .env 中找到')
    return m.group(1)


def ocr_frame(path, key, retries=4):
    b64 = base64.b64encode(open(path, 'rb').read()).decode()
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        {"type": "text", "text": PROMPT}]}]}).encode()
    last = None
    for att in range(retries + 1):
        try:
            req = urllib.request.Request(BAILIAN_URL, data=body, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=120).read())
            txt = (r['choices'][0]['message'].get('content') or '').strip()
            tok = r.get('usage', {}).get('total_tokens', 0)
            if not txt:
                # 空 content 必须当失败——不能把空串写成"无文字"然后落盘
                raise RuntimeError('空 content')
            return LOC_RE.sub('', txt), tok
        except urllib.error.HTTPError as e:
            last = e
            time.sleep(8 * (att + 1) if e.code == 429 else 3)
        except Exception as e:
            last = e
            time.sleep(3)
    return f"__ERR__{type(last).__name__}", 0


def sec_of(path):
    m = re.search(r'(\d+)', os.path.basename(path))
    return int(m.group(1)) if m else 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    frame_dir = sys.argv[1]
    workers = 6
    if '--workers' in sys.argv:
        workers = int(sys.argv[sys.argv.index('--workers') + 1])
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(frame_dir, 'ocr.json')

    frames = sorted(glob.glob(os.path.join(frame_dir, '*.jpg')), key=sec_of)
    if not frames:
        print(f"❌ {frame_dir} 里没有 jpg 帧")
        return 1
    key = api_key()
    done = json.load(open(out)) if os.path.exists(out) else {}
    todo = [p for p in frames if os.path.basename(p) not in done]
    print(f"总 {len(frames)} 帧 / 已完成 {len(done)} / 待处理 {len(todo)}（并发 {workers}）", flush=True)

    t0, tok_total, n = time.time(), 0, 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(ocr_frame, p, key): p for p in todo}
        for f in as_completed(futs):
            p = futs[f]
            txt, tok = f.result()
            done[os.path.basename(p)] = txt
            tok_total += tok
            n += 1
            if n % 20 == 0:
                json.dump(done, open(out, 'w'), ensure_ascii=False)
                el = time.time() - t0
                print(f"  [{n}/{len(todo)}] {el:.0f}s 预计剩余 {el/n*(len(todo)-n):.0f}s tokens={tok_total}", flush=True)
    json.dump(done, open(out, 'w'), ensure_ascii=False)

    # 合并连续重复帧 → 时间轴（1fps ⇒ 帧号即秒）
    lines = []
    for k in sorted(done, key=sec_of):
        v = done[k]
        if not v or v.upper() in ('NONE', '无文字') or v.startswith('__ERR__'):
            continue
        v = re.sub(r'\s+', '', v)
        if lines and lines[-1][1] == v:
            lines[-1][0].append(sec_of(k))
        else:
            lines.append([[sec_of(k)], v])
    tl = [f"[{ts[0]:>4}-{ts[-1]:<4}s] {txt}" for ts, txt in lines]
    open(os.path.join(frame_dir, 'timeline.txt'), 'w', encoding='utf-8').write('\n'.join(tl))
    open(os.path.join(frame_dir, 'script_full.txt'), 'w', encoding='utf-8').write(''.join(t for _, t in lines))

    print(f"\n=== 完成 {len(done)} 帧 / 耗时 {time.time()-t0:.0f}s / tokens={tok_total} "
          f"/ 估算费用 ≈ ¥{tok_total/1e6*0.3:.4f} ===")
    print(f"    有效字幕 {len(lines)} 段 → timeline.txt / script_full.txt")
    return 0


if __name__ == '__main__':
    sys.exit(main())
