# XLSX 样式表不兼容处理

## 问题现象

某些 .xlsx 文件（尤其是政府项目报送的表格）在 openpyxl 中打开时报错：

```
TypeError: expected <class 'openpyxl.styles.fills.Fill'>
```

**根因**：文件中的 `xl/styles.xml` 使用了旧版或非标准的 Fill 定义，导致 openpyxl 解析 stylesheet 时崩溃。即使使用 `data_only=True` 也无法跳过——openpyxl 在读取 workbook 之前就会解析 styles。

## 解决方案：直接解析 XML

openpyxl 失败时，直接通过 `zipfile` 解压读取内部 XML：

```python
import zipfile, xml.etree.ElementTree as ET

with zipfile.ZipFile('file.xlsx') as z:
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    
    # 1. 读共享字符串表
    ss_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    shared_strings = []
    for si in ss_root.findall('.//s:si', ns):
        texts = []
        for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
            if t.text: texts.append(t.text)
        shared_strings.append(''.join(texts))
    
    # 2. 读单元格值的辅助函数
    def cell_val(c):
        v = c.find('s:v', ns)
        t = c.get('t', '')
        if v is not None and v.text:
            if t == 's':  # 共享字符串索引
                idx = int(v.text)
                return shared_strings[idx] if idx < len(shared_strings) else v.text
            return v.text  # 直接值（数字、日期序列号）
        return ''
    
    # 3. 读 sheet 数据
    root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    rows = root.findall('.//s:row', ns)
    for r in rows:
        cells = r.findall('s:c', ns)
        col_map = {}
        for c in cells:
            col_letter = ''.join(filter(str.isalpha, c.get('r', '')))
            col_map[col_letter] = cell_val(c)
        # col_map['A']~ 为各列值
```

## Excel 日期序列号转换

日期存为数字（如 `46183`）时需转换为实际日期：

```python
from datetime import datetime, timedelta

def excel_to_date(serial):
    if not serial or not serial.strip():
        return None
    try:
        days = float(serial)
        if days < 1: return None
        # Excel epoch: 1899-12-30
        base = datetime(1899, 12, 30)
        return base + timedelta(days=days)
    except:
        return None
```

## 限制

- XML 解析不能处理合并单元格的自动填充
- 不能应用样式（颜色、字体、边框）
- 公式只返回缓存值（同 openpyxl `data_only=True`），不含公式文本
- 多个 sheet 需分别读取 `xl/worksheets/sheetN.xml`

## 适用场景

仅当 openpyxl 因 styles.xml 解析失败时报错时使用此方案。正常情况下仍优先使用 openpyxl。
