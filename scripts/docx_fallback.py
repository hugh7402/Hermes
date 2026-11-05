#!/usr/bin/env python3
"""docx/doc fallback converter for ingest_docs.py.

When MarkItDown fails on a .docx (corrupt relationship such as 'word/../NULL'),
fall back to reading word/document.xml directly with lxml: join all w:t runs,
break on w:p, and emit table cells pipe-separated.
Usage: python3 docx_fallback.py <file.docx>
Prints plain markdown-ish text to stdout.
"""
import sys
import zipfile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def convert(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = etree.fromstring(xml)
    body = root.find(W + "body")
    if body is None:
        body = root
    out = []
    for node in body.iter():
        tag = node.tag
        if tag == W + "p":
            parts = []
            for t in node.iter():
                if t.tag == W + "t" and t.text:
                    parts.append(t.text)
                elif t.tag == W + "tab":
                    parts.append("\t")
                elif t.tag == W + "br":
                    parts.append("\n")
            line = "".join(parts).strip()
            out.append(line)
        elif tag == W + "tbl":
            for tr in node.findall(W + "tr"):
                cells = []
                for tc in tr.findall(W + "tc"):
                    txt = "".join(
                        t.text for t in tc.iter() if t.tag == W + "t" and t.text
                    ).strip()
                    cells.append(txt)
                row = " | ".join(c for c in cells if c)
                if row:
                    out.append(row)
    # de-duplicate because tables nest inside paragraphs iteration order
    seen = set()
    lines = []
    for ln in out:
        if not ln:
            continue
        key = (ln, len(lines))
        if ln in seen and len(ln) < 40:
            continue
        seen.add(ln)
        lines.append(ln)
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.write(convert(sys.argv[1]))
