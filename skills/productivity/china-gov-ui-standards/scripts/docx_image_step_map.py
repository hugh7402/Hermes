#!/usr/bin/env python3
"""docx 内嵌截图 ↔ 上文档落 精确映射

场景：一份「带系统截图的演示脚本 / 操作说明」docx，需要知道**哪张截图对应哪一步**。
markitdown 会把图片变成占位符、丢失对应关系；本脚本按段落顺序取 <a:blip r:embed>，
查 rels 拿媒体文件名，恢复「序号 | 媒体文件 | 上文段落」的映射。

用法：
    python3 docx_image_step_map.py <file.docx>
    python3 docx_image_step_map.py <file.docx> --out ./imgs --width 90

输出：
    stdout               映射表（序号 = 文档顺序）
    <out>/               图片本体（文档内嵌媒体按原名抽出）

注意：同一张媒体可能在正文里被引用多次（映射表出现同名不同序号）——**序号才是文档顺序**。
依赖：python-docx（本机用 /opt/data/.venv/bin/python3 跑）
"""
import argparse
import pathlib
import sys
import zipfile


def main():
    ap = argparse.ArgumentParser(description='docx 内嵌图片 ↔ 上文档落 映射')
    ap.add_argument('docx')
    ap.add_argument('--out', help='抽出图片的目录（不给则只打印映射表）')
    ap.add_argument('--width', type=int, default=70, help='上文截断长度，默认 70')
    a = ap.parse_args()

    try:
        import docx
        from docx.oxml.ns import qn
    except ImportError:
        sys.exit('需要 python-docx（本机：/opt/data/.venv/bin/python3）')

    p = pathlib.Path(a.docx)
    if not p.exists():
        sys.exit(f'找不到文件：{p}')

    d = docx.Document(str(p))
    rels = {rid: r.target_ref for rid, r in d.part.rels.items()}

    # 按段落顺序走：记住「上方最近的文字」，遇到图片就把当前缓存配给它
    order, cur = [], []
    for para in d.paragraphs:
        t = para.text.strip()
        if t:
            cur.append(t)
        for blip in para._p.findall('.//' + qn('a:blip')):
            rid = blip.get(qn('r:embed'))
            target = rels.get(rid, '?')
            order.append({'n': len(order) + 1,
                          'media': pathlib.Path(target).name,
                          'after_text': cur[-1] if cur else ''})
            cur = []

    print(f'{p.name}：共 {len(order)} 张内嵌图片\n')
    for o in order:
        print(f"[{o['n']:3d}] {o['media']:16s} ← {o['after_text'][:a.width]}")

    if a.out:
        dest = pathlib.Path(a.out)
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.startswith('word/media/'):
                    data = z.read(name)
                    if data:
                        (dest / pathlib.Path(name).name).write_bytes(data)
                        n += 1
        print(f'\n→ 抽出 {n} 个媒体文件到 {dest}')


if __name__ == '__main__':
    main()
