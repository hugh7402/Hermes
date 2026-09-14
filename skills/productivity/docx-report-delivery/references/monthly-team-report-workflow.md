# 团队月度重点项目汇报材料 — 生成工作流

适用：联通数智-智慧民政项目组每月上报的《团队月度重点项目汇报材料》（docx）。

## 成品格式基线（继承上一期，勿重设）

| 元素 | 规格 |
|---|---|
| 标题 | 18pt 粗体居中（Normal 样式 + 手动字体设置） |
| 团队信息行 | 10pt 居中：`团队名称：联通数智-智慧民政项目组   汇报人：` |
| 汇报时间行 | 10pt 居中：`汇报时间：<年>年<月>月` |
| 章节标题 | Heading 2：一、…六、 |
| 正文段 | Normal，`1. ` 编号起头，无首行缩进 |

## 生成方法：模板段落深拷贝

复制上一期 docx → `Document()` 打开 → `copy.deepcopy` 各类型段落元素（title / info1 / info2 / H2 / 编号正文）→ 清空 body 内 `w:p`（**保留 `sectPr`**）→ 按内容顺序 `body.insert` 回 → save。

骨架：

```python
import shutil, copy, os
from docx import Document
from docx.oxml.ns import qn

shutil.copy(SRC, DST)
d = Document(DST)
p = d.paragraphs
title_elm, info1_elm, info2_elm = (copy.deepcopy(p[i]._element) for i in (0, 1, 2))
h2_elm, num_elm = copy.deepcopy(p[3]._element), copy.deepcopy(p[4]._element)

def set_text(elm, text):          # 只改第一个 run，字体/字号/缩进全部继承
    runs = elm.findall(qn('w:r'))
    for r in runs[1:]:
        elm.remove(r)
    t = runs[0].find(qn('w:t')) if runs else None
    if t is None:
        t = runs[0].makeelement(qn('w:t'), {}); runs[0].append(t)
    t.text = text

body = d.element.body
sectPr = body.find(qn('w:sectPr'))          # 必须保留
for q in list(body.findall(qn('w:p'))):
    body.remove(q)
for kind, text in content:                   # content = [('title', …), ('h', …), ('num', …)]
    elm = copy.deepcopy({'title': title_elm, 'info1': info1_elm, 'info2': info2_elm,
                         'h': h2_elm}.get(kind, num_elm))
    set_text(elm, text)
    body.insert(list(body).index(sectPr), elm)
d.save(DST)
```

- 段落索引与 `docx_read.py --structure` 的 outline 对应（0=title, 1=info1, 2=info2, 3=H2, 4=正文…）
- 复用脚本：`/opt/data/scripts/gen_report_docx.py`（2026-08-22 生成 7-8 月版时写的，策略=复制 6 月版当模板）

## 数据源 → 章节映射

| 章节 | 数据来源 |
|---|---|
| 一、重点业务产品打造情况 | 双周汇报「二、重点工作落实情况」——业务看板 / 民政通改版 / 民政大脑综合画像 / 电子档案一键归档等产品线 |
| 二、重点项目攻坚与落地成果 | 双周汇报「一、本双周整体工作推进情况」——任务总数、当期完成率、累计进度、延期数 + 各系统开发进展 |
| 三、商机拓展与储备转化情况 | 双周汇报通常没有——须问用户 |
| 四、现存问题、卡点与风险事项 | 双周汇报「三、当前存在的主要问题及建议」+ 延期任务构成拆解 |
| 五、工作计划与攻坚举措 | 下一双周任务量（当期 + 延期待办）+ 四项攻坚方向 + 双周汇报的建议条款 |
| 六、其他事项 | 留空，团队自填 |
| （平台运行数据，可写入二） | 月度报告 md（知识库 `concepts/`） |

## 读双周汇报 PDF：过滤表格行

```python
lines = [l.strip() for l in t.split('\n')]
body = [l for l in lines if not (l.startswith('|') or l.startswith('---'))]
# 再滤掉纯数字行（页码）与空行
```

不过滤的话正文被表格行切碎，看起来像内容缺失（实际 4272 字正文 vs 24767 字符全文）。
附件任务明细表单独按 `|` 行解析：责任处室、责任人、计划完成日期、「已延期」标记。

## 交付

- 目录：`/opt/data/OutPut Box/团队月度重点项目汇报材料_<YYYY年M月>/`，放 docx + `汇报材料.md` 源稿（与 7-8 月版目录体例一致）
- 微信发送前 `cp` 到无空格路径，再在回复里写 `MEDIA:/opt/data/<文件名>.docx`

## 已产出记录

| 期次 | 生成日期 | 段数 | 数据源 | 备注 |
|---|---|---|---|---|
| 2026 年 7 月-8 月 | 2026-08-22 | 28 | 7 月月度报告 + 第六双周汇报 + 用户 Excel | `gen_report_docx.py` 的诞生版；一、六段留空 |
| 2026 年 9 月 | 2026-09-11 | 26 | 第七个双周工作汇报（8 月 24 日-9 月 6 日） | 三、商机与六、其他留空；缺 9 月平台运行数据、9/7-9/10 进展，已列清单请用户补 |
