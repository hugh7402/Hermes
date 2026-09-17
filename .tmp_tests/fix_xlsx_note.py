"""一次性补救：顶规政策要点(1).xlsx 因 openpyxl Fill 样式损坏无法用 markitdown 转换。
直接解析 xlsx 内部 XML（zip）提取内容，产出 markdown，走正常入库流程。"""
import zipfile, re, sys, os
# 注：xl/sharedStrings.xml 与 sheet XML 均来自本地可信文件（用户自有 xlsx，非外部输入），
# 且 stdlib ET 不解析外部实体（无 DTD 处理），此处无 XXE 风险。
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, '/opt/data')
import ingest_docs as ing

SRC = "/opt/data/WebChat BackUp/文档/01_联通材料/01_政策法规/顶规政策要点(1).xlsx"
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

z = zipfile.ZipFile(SRC)
shared = []
if 'xl/sharedStrings.xml' in z.namelist():
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    for si in root.findall('m:si', NS):
        shared.append(''.join(t.text or '' for t in si.iter(
            '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')))

# 工作表名
wbroot = ET.fromstring(z.read('xl/workbook.xml'))
sheetnames = [s.get('name') for s in wbroot.iter(
    '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet')]

out = []
for idx, sname in enumerate(sheetnames, 1):
    path = f'xl/worksheets/sheet{idx}.xml'
    if path not in z.namelist():
        continue
    root = ET.fromstring(z.read(path))
    out.append(f"## {sname}\n")
    for row in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
        cells = []
        for c in row.findall('m:c', NS):
            v = c.find('m:v', NS)
            if v is None or v.text is None:
                cells.append('')
                continue
            if c.get('t') == 's':
                cells.append(shared[int(v.text)])
            else:
                cells.append(v.text)
        while cells and cells[-1] == '':
            cells.pop()
        if any(x.strip() for x in cells):
            out.append('\t'.join(x.replace('\n', ' ') for x in cells))
    out.append('')

text = '\n'.join(out).strip()
print(f"提取完成：{len(sheetnames)} 个工作表，{len(text)} 字符")
print(text[:400])

name = os.path.basename(SRC).rsplit('.', 1)[0] + '.md'
path = ing.save_note(name, text)
print(f"\n✅ 写入 concepts/{os.path.basename(path)}")
