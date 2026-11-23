# PPT 模板库 · 清单

做 PPT 前先看这里，**给用户列可选模板让他挑**，不要默认某个。

## A. 已入库的自有模板（`/opt/data/ppt-templates/`）

| 模板 ID | 说明 | 适用 | 规范文件 |
|---|---|---|---|
| `数智公司` | 联通数据智能有限公司汇报模板，白底＋联通红 `#E60012`＋微软雅黑，含母版红线条/logo/页码 | 公司内部汇报、对上汇报、项目汇报 | `数智公司/TEMPLATE.md` |

用法：
```bash
# 基于它生成（母版自带品牌元素，最保真）
cp /opt/data/ppt-templates/数智公司/数智公司PPT模板.pptx /tmp/work.pptx
```

## B. ppt-master 自带布局模板（`templates/layouts/`）

按用途挑，通过主流程 Step 3 显式传模板目录路径使用。

| 模板 ID | 页数 | 适用场景 |
|---|---|---|
| `government_blue` | 5 | 重点项目汇报、五年规划、工作总结、政务 |
| `government_red` | 5 | 政务汇报、政策解读、工作总结、项目介绍 |
| `ai_ops` | 6 | 电信 AI 运营架构、IT 系统总览、数字化转型方案、智能基础设施 |
| `academic_defense` | 5 | 论文答辩、学术报告、研究进展、课题申报 |
| `medical_university` | 5 | 医学学术报告、病例讨论、科研汇报、医院汇报 |
| `psychology_attachment` | 5 | 心理治疗培训、学术讲座、咨询案例分析 |
| `pixel_retro` | 5 | 技术分享、编程教程、游戏介绍、极客风 |

## C. ppt-master 自带品牌预设（`templates/brands/`）

只定视觉身份（配色/字体/logo/口径），不提供页面清单。

| 品牌 | 主色 | 适用 |
|---|---|---|
| `中国电建` | `#00418D` | 工程项目报告、技术方案、商务谈判、企业宣传 |
| `中汽研` | `#004098` | 产品认证、测评报告、汽车行业 |
| `anthropic` | `#D97757` | AI/LLM 技术分享、开发者大会 |
| `google` | `#4285F4` | 多产品企业演示、开发者活动 |

## 查索引

```bash
S=/opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master
cat $S/templates/layouts/layouts_index.json
cat $S/templates/brands/brands_index.json
```

## 新增自有模板的流程

1. 把 `.pptx` 放进 `/opt/data/ppt-templates/<模板ID>/`
2. 跑 intake 抽规范：
   ```bash
   python3 /opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/scripts/pptx_intake.py \
     /opt/data/ppt-templates/<模板ID>/<文件>.pptx \
     -o /opt/data/ppt-templates/<模板ID>
   ```
3. 写 `<模板ID>/TEMPLATE.md`：画幅、配色、字体、页型坐标、**占位符类型（BODY 还是 TITLE）**、槽位够不够填
4. 在本文件 A 表加一行
