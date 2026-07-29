# XLS/XLSX Extraction

## xlrd (for .xls)

```python
import xlrd
wb = xlrd.open_workbook('file.xls')
print(f'SHEETS: {wb.sheet_names()}')
for name in wb.sheet_names():
    sh = wb.sheet_by_name(name)
    print(f'\n=== {name} ({sh.nrows}r x {sh.ncols}c) ===')
    for r in range(min(sh.nrows, 120)):
        vals = [str(sh.cell_value(r, c)) for c in range(sh.ncols)]
        print(' | '.join(vals))
```

Run:
```bash
uv run --with xlrd python3 -c "<code>"
# Or via file-indirection if blocked:
uv run --with xlrd python3 /tmp/extract_xls.py
```

## openpyxl (for .xlsx)

```python
import openpyxl
wb = openpyxl.load_workbook('file.xlsx', data_only=True)
for name in wb.sheetnames:
    ws = wb[name]
    print(f'\n=== {name} ({ws.max_row}r x {ws.max_column}c) ===')
    for row in ws.iter_rows(values_only=True):
        print(' | '.join(str(c or '') for c in row))
```

Run:
```bash
uv run --with openpyxl python3 -c "<code>"
```

## Determine file type

```bash
file "unknown_file.xls"
```

If output says "Microsoft Excel 2007+" → use openpyxl.  
If output says "Composite Document File V2" → use xlrd.
