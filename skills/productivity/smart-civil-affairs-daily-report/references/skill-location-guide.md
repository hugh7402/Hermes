# Skill Location Guide

This skill lives at:
- **Skill directory**: `/opt/data/skills/productivity/smart-civil-affairs-daily-report/`
- **SKILL.md**: `productivity/smart-civil-affairs-daily-report/SKILL.md`
- **Main script**: `scripts/generate_report.py` (full path: `.../smart-civil-affairs-daily-report/scripts/generate_report.py`)

## Why `skills_list` / `/skill` might not find it

`skills_list()` scans only first-level directories under `/opt/data/skills/`. This skill is nested under `productivity/`, so it may not appear in `skills_list()` output unless you drill into that category.

To find it programmatically:
```python
from hermes_tools import search_files
search_files(pattern="smart-civil-affairs*", target="files", path="/opt/data/skills", limit=5)
```

## User trigger phrases

The user invokes this skill by saying:
- "启动陕西智慧民政项目日报"
- "启动 smart-civil-affairs-daily-report"
- "给我出一版日报" (in context of 陕西智慧民政)
- "生成日报" (in context of 陕西智慧民政)

When any of these surface, the correct action is:
1. Find latest xlsx in `/opt/data/cache/documents/` matching `双周任务和问题清单-*.xlsx`
2. Run `scripts/generate_report.py <xlsx_path>` to produce Word doc
3. Output goes to `/opt/data/OutPut Box/陕西智慧民政项目日报-{日期}.docx`
