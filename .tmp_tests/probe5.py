from markitdown import MarkItDown
import os
md = MarkItDown()
paths = [
 "/opt/data/WebChat BackUp/文档/01_联通材料/01_政策法规/顶规政策要点(1).xlsx",
 "/opt/data/WebChat BackUp/文档/01_联通材料/02_标准规范/3.主数据技术规范/主数据标准技术规范20260125-v2.docx",
 "/opt/data/WebChat BackUp/文档/01_联通材料/02_标准规范/3.主数据技术规范/主数据标准技术规范20260126-v1.docx",
 "/opt/data/WebChat BackUp/文档/协同创新仿真实验平台_北京数据局/北京数字资源/汇报材料_0921/北京IRM系统截图2025年9月21日105451.docx",
 "/opt/data/WebChat BackUp/文档/协同创新仿真实验平台_北京数据局/图片修改.pptx",
]
for p in paths:
    name = os.path.basename(p)
    try:
        r = md.convert(p)
        t = (r.text_content or '').strip()
        print(f"OK  {len(t):>7} 字 | {name}")
        print("    head:", t[:150].replace("\n", " / "))
    except Exception as e:
        print(f"ERR {type(e).__name__}: {str(e)[:160]} | {name}")
