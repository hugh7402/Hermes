import fitz, os, json
p = '/opt/data/WebChat BackUp/文档/20260819_具身智能训练场研究报告2026年发布.pdf'
doc = fitz.open(p)
total_text = 0
for i in range(min(3, doc.page_count)):
    total_text += len(doc[i].get_text().strip())
print(json.dumps({
    'pages': doc.page_count,
    'size_mb': round(os.path.getsize(p)/1024/1024, 1),
    'first3_pages_text_chars': total_text,
    'img_pages': sum(1 for i in range(doc.page_count) if doc[i].get_images())
}))
