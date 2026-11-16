# 截图类证据交付物的台账与维护配方

> 出处：2026-10-11 四川一体化数据资源管理系统原型（V2.4→V2.5 轮）——
> 该轮发现 5 张历史截图「名不副实」（V2.0 权限门之后的空态/拦截条），全部重拍、删掉 1 张过时图。
> 项目根：`/opt/data/designs/drs-demo`；两个截图目录：`交付/截图_真机/`（交付）与 `screenshots_真机/`（源，`package.py` 的回拷来源）。

## 一、出图脚本台账（“哪张图是谁产的”必须先摸清）

摸排命令（**每次复审先跑这个**）：

```bash
for f in *.py; do
  n=$(grep -c screenshot "$f")
  dirs=$(grep -o 'screenshots_真机\|截图_真机' "$f" | sort -u | tr '\n' ',')
  nums=$(grep -o "[0-9][0-9]b\?_[^'\"]*\.png" "$f" | cut -c1-3 | sort -u | tr '\n' ' ')
  role=$(grep -c setRole "$f"); st=$(grep -c 'S.done\|taskRun\|taskStatus' "$f")
  printf "%-24s 图:%-3s 目录:%-22s 图号:%-20s setRole:%s 状态:%s\n" "$f" "$n" "${dirs:-?}" "${nums:-?}" "$role" "$st"
done
```

本项目实测（历史版本脚本，注意其中三个**不设角色**）：

| 脚本 | 图号 | 写入目录 | setRole | 状态 |
|---|---|---|---|---|
| `verify_refit.py` / `verify_chrome.py` / `verify_feedback.py` / `geom_check.py` / `verify_debug.py` / `e2e_demo.py` | 01~31 等 | 源 | 有 | 部分有 |
| `shots_v12.py` | 32 导入解析结果 / 33 目录列表 / 34 审批管理多条待审核 | 源 | ❌ | ❌ |
| `shots_v13.py` | 35~38（数据项/归集方式/规则库） | 源 | ✅ | ❌ |
| `shots_v14.py` | 39 前置数据库既有表 / 40 归集库归集前无表 / 41 问题清单 | 源 | ❌ | ❌ |
| `shots_v15.py` | 41 问题清单（政治面貌）/ 42 保留原值视窗 | 源 | ❌ | ❌ |
| `render_baoyu_shots.py` / `render_dirs_shots.py` | 少量 | 源 | ❌ | ❌ |
| `final_v22.py`（由 final_v20/18 派生，**版本号写入段已剔除**） | 51~54（权限门/前置库/必填类问题） | 交付 | ✅ | ✅ |
| `reshot_extras.py`（由 final_v18 + V2.1 脚本抽段合成） | 45~49 / 55 / 56 | 交付 | ✅ | ✅ |
| `reshot50.py`（`polish_v18.py` 抽段） | 45 / 46 / 50 | 交付 | ✅ | ✅ |
| `reshot5.py` | 11b 编辑表结构 / 16 一数一标准 / 43–44 导入民政·人社目录 | 交付 | ✅ | ✅ |
| `check_actbar.py` | 22b 问题清单底栏 | 交付 | ✅ | ✅ |
| `reshot_states.py`（本轮新增，防回退） | 34 / 39 / 40 / 41 / 42 | 交付 | ✅ | ✅ |

⚠️ **派生脚本的铁律**：从旧的收尾脚本抄出图段时，**必须剔掉它里面的「升版/改版本号」动作**
（`final_v18.py` / `final_v20.py` / `polish_v18.py` 都会 `re.sub("VER = ...")` 并改写 `app.js` 的 `VERSION`）——
直接跑它们会把产物降回旧版本号。安全的是 `shots_v12~v15`、`reshot_*`、`check_actbar`。

## 二、状态配方（抄专项测试，别自己编）

**A. 治理已执行完（问题清单/明细视窗可点）**

```js
(() => { const S = window.APP.S, g = S.govern;
  S.catalogs[0].status = '已发布'; S.catalog = S.catalogs[0];
  S.done = {cat:true,audit:true,pub:true,col:true,biz:true,tech:true,table:true,colrun:true,gconf:true,grun:true};
  g.taskStatus = '已上线'; g.taskRun = 'done';
  g.source = { relate:true, authority:'四川省自然人基础信息权威库（公安人口库）',
               table:'authority_natural_person', main:'身份证件号码',
               verify:'政治面貌', strategy:'保留原值' };
  window.APP.setRole('govern'); })()
```

**B. 归集前（归集库 0 张表 + 前置库 6 张既有表列表）**

```js
(() => { const S = window.APP.S, c = S.collect;
  S.catalogs[0].status = '已发布'; S.catalog = S.catalogs[0];
  S.done = {cat:true,audit:true,pub:true,col:true,biz:true,tech:true,table:false,colrun:false,gconf:false,grun:false};
  c.status = '技术审核通过'; c.techAuditAt = '2026-10-11 09:30:00';
  c.table = c.table || 'db_natural_person_base';
  c.tables = { '前置仓': { name:'ods_'+c.table, label:'前置仓表', created:'2026-10-08 09:12:00' },
               '归集仓': { name:'dwd_'+c.table, label:'归集仓表', created:c.techAuditAt } };
  c.taskRun = false;
  window.APP.setRole('collect'); })()
```

⚠️ **`c.tables` 不给，前置库那 6 张表的清单不渲染**（只剩对照卡上的汇总数）—— 这就是「图名叫『既有表』但图里没有表」的成因。

**C. 「多条待审核」的审批列表**：先 `setRole('editor')` → 上传 `政务数据目录编目模板.xlsx`（6 条）→ 关掉弹窗 →`setRole('audit1')` → `go('s2')`。

**D. 抽屉类图（视窗）必须先点开再截图**，且要点对入口：

```js
// 保留原值视窗 / 转换视窗：先切页签，再点行内链接
document.querySelector('[data-tab="保留原值"]').click();
document.querySelector('[data-view-p]').click();   // 抽屉标题会带“· 第 N 条”
```

⚠️ 旧脚本里 `shots_v15.py` 的 42 号**只点了页签就截图**，从未打开抽屉 —— 图名却写着「视窗」。
**凡图名含「视窗 / 详情 / 抽屉」的，截图前必须断言 `#drawer.on` 或 `#drawer-foot .btn` 存在。**

## 三、合并、校验、删图

```python
# 两个目录互扫（交付优先），再打包
for f in SRC.glob('*.png'):
    if not (D / f.name).exists(): (D / f.name).write_bytes(f.read_bytes())
for f in D.glob('*.png'): (SRC / f.name).write_bytes(f.read_bytes())
# 校验：张数 + 逐字节
mism = [f.name for f in D.glob('*.png') if not (SRC / f.name).exists()
        or (SRC / f.name).read_bytes() != f.read_bytes()]
print(f'交付 {len(list(D.glob("*.png")))} 张｜源 {len(list(SRC.glob("*.png")))} 张｜不一致 {len(mism)}')
```

**删图规则**：图名描述的数据状态已不存在时必须删（本轮删掉「41_问题清单_保留原值联系电话」——
V1.5 起该问题字段已改成政治面貌/兵役状况/宗教信仰/民族）。
**删了就要在回复里点名说清“删了哪张、为什么”**，否则用户会以为丢了证据。

## 四、本轮修好的 5 张（回归基线）

| 图 | 修前 | 修后 |
|---|---|---|
| 34 审批管理_多条待审核 | 编目员视角，列表被权限条压着 | audit1 角色 + 导入 6 条 → 6 行待审核 |
| 39 前置数据库_既有表 | 只有汇总数，没有表清单 | `c.tables` 状态 → 列全 6 张（含「本次工单」标记） |
| 40 归集数据库_归集前无表 | 状态不清 | 归集前 0 张表 · 0 行 + 空态提示 |
| 41 问题清单_保留原值政治面貌 | 空态 | 治理已执行 + govern 角色 → 12 行 |
| 42 保留原值视窗_政治面貌冲突 | 空态 + 权限条（且从未打开抽屉） | 真抽屉：标题「保留原值视窗：第 41 条」+ 群众→共青团员 对比 |
