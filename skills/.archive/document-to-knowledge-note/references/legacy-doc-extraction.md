# 老 .doc（legacy Word）文本提取（2026-08-05 实测）

## 背景

用户通过微信发来 `.doc`（WPS 保存的旧格式，非 .docx）。本服务器：
- ❌ 无 pandoc / soffice / libreoffice（无 root 权限，apt 装不了）
- ❌ markitdown 0.1.7 实测报 `UnsupportedFormatException`（**只支持 .docx，不支持老 .doc**）
- ❌ antiword / catdoc / wvText 均未安装
- ✅ 唯一可行：`olefile` 解析 OLE2 复合文档 → WordDocument 流 → UTF-16LE 解码

## 安装

```bash
uv pip install --python /opt/data/ocr_venv/bin/python3 olefile
```

## 提取脚本

```python
import olefile, re

doc = "/path/to/xxx.doc"
ole = olefile.OleFileIO(doc)
print(ole.listdir())  # 确认流：常见有 WordDocument / 0Table / Data / SummaryInformation

wd = ole.openstream("WordDocument").read()
# 正文文本从偏移 0x800 起，UTF-16LE 编码
s = wd[0x800:].decode("utf-16-le", errors="ignore")

lines = [l.strip() for l in s.split("\r") if len(l.strip()) > 1]

# 过滤目录/超链接垃圾行（TOC 域代码）
body = [l for l in lines
        if not l.startswith("\x13TOC") and not l.startswith("\x13 HYPERLINK")
        and "PAGEREF" not in l and "HYPERLINK" not in l]

print("\n".join(body))
```

## 实测要点（WPS 生成的操作手册 .doc，14MB）

- 文件头 `d0cf11e0a1b11ae1` = OLE2 复合文档（.doc 标准格式）
- `strings -e l`（UTF-16LE 模式）只能拿到流名/元数据，**正文提取靠上面的 olefile 方案**
- 该文档正文主要是**截图**（IMG_256 系列占多数），文字层只有目录+说明文字——对提取正文说明文字足够，但图片内容需另走 OCR
- 解码后含 `\x13TOC \o "1-4"` 等域代码残留，按上面过滤规则去掉
- `errors="ignore"` 必须加，否则解码中断

## 判定顺序（.doc 来了先试哪个）

1. `read_file` 工具自动提取（对 .docx 有效；**老 .doc 无效**）
2. markitdown → 只支持 .docx
3. **olefile 方案（本环境唯一可靠路径）**

## 关联

- 同类：.xls 旧格式用 `xlrd`（openpyxl 失败时），见 SKILL.md Step 2 表
- 若文件是 WPS 保存的 .doc 且正文全是截图，提取文字层后仍需对图片走 OCR（image-ocr / ocr-and-documents）
