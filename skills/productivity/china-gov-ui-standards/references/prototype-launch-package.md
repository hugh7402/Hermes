# 启动包：把原型做成「已部署的本机系统」（每屏一条 URL）

> 2026-10-11 实测通过。适用场景：**用户要在评审/汇报现场把单文件 HTML 原型当真实系统演示**，
> 且明确要求"显示地址栏 + `http://localhost:8080/`"（而**不是**隐藏地址栏的应用模式 ——
> 藏地址栏那版被用户否掉了，理由见 SKILL.md 第十节「最终形态」）。
> 上位说明与痕迹清单见 `references/demo-anti-tell-packaging.md`；本文件只讲**怎么把它跑起来**。

## 一、成品包形状（用户点名要的包名与文件）

```
四川一体化数据资源管理系统-启动包/
├── index.html      # 页面（名字必须是 index.html —— 这样地址栏才是干净的 localhost:8080/）
├── serve.py        # 静态服务 + 单页回退（★ 必需，见第三节）
├── 启动.command    # macOS 双击启动（Mac 用户主用这个）
├── 启动.sh         # Linux/命令行用户
└── 使用说明.md     # 含下方「地址表」，用户可直接照着跳页
```

- 包名/文件名**不带"演示"二字**（用户明确要求）；页面内也不带（含页脚版本号，见痕迹清单）。
- 页面与开发版是**两个产物**：演示版只去痕迹（页脚版本号、Ctrl+D 调试开关、`APP.VERSION`），**功能一字不动**。
  对照验收：开发版页脚有版本号 / 演示版没有；Ctrl+D 在演示版无效；切屏功能未变。

## 二、地址表（本项目已定的 17 条，直接抄改即可）

| 路径 | 屏 | 路径 | 屏 |
|---|---|---|---|
| `/` | 默认屏（→ 统一成 `/xzzwsjml`） | `/lxgjrw` | 离线归集任务 |
| `/xzzwsjml` | 新增政务数据目录 | `/mlgjzt` | 目录归集状态 |
| `/sjmllb` | 数据目录列表 | `/sjzlgzpz` | 数据治理规则配置 |
| `/sjmlspgl` | 数据目录审批管理 | `/gzpzspgl` | 规则配置审批管理 |
| `/gjgdywsh` | 归集工单业务审核 | `/zlrwgl` | 治理任务管理 |
| `/sjgjgd` | 数据归集工单 | `/rwslywgl` | 任务实例运维管理 |
| `/gjgdsh/djs` | 归集工单审核（待技术审核）**二级路径** | `/sjqxjgmx` | 数据清洗结果明细 |
| `/gjgdsh/ybj` | 归集工单审核（已办结）**二级路径** | `/zlcxzl` | 治理成效总览 |
| `/qzsjk` | 前置数据库 | `/gjsjk` | 归集数据库 |

命名规则：**屏名拼音首字母**（用户指定），子视图用二级路径。**不用中文、不用英文单词** —— 拼音首字母是用户的原话要求。

## 三、三处实现（缺一处就不成立）

### ① 服务：单页回退 —— `templates/spa_serve.py`

```bash
python3 serve.py 8080        # 只监听 127.0.0.1；未命中的路径回退 index.html
```

🚨 **`python3 -m http.server` 不行**：`/sjqxjgmx` 在那台服务上没有这个文件 → **404**，
浏览器显示"无法访问"，用户会以为路由写坏了。**这是本方案唯一的硬依赖。**

### ② 前端路由（在 `go()` 里 pushState；启动按路径落屏）

```js
var ROUTES = { xzzwsjml:'s1', sjmllb:'s1b', sjmlspgl:'s2', gjgdywsh:'s3','gjgdsh/djs':'s3b',
               'gjgdsh/ybj':'s3c', sjgjgd:'s4', qzsjk:'s5', gjsjk:'s6', lxgjrw:'s7',
               mlgjzt:'s8', sjzlgzpz:'s1c', gzpzspgl:'s2b', zlrwgl:'s4b', rwslywgl:'s4c',
               sjqxjgmx:'s7c', zlcxzl:'s8b' };
var PATHOF = {};                                  // 反向表：屏 -> 路径
Object.keys(ROUTES).forEach(function (k) { PATHOF[ROUTES[k]] = k; });

function fromPath(p) {                            // 未知路径返回 null
  p = String(p || '').replace(/^\/+|\/+$/g, '');
  return ROUTES[p] || null;
}

/* 系统内切屏时改地址栏（不刷新）。noPush=true 时不写历史（启动落屏/popstate 回放）*/
function pushRoute(sc, noPush) {
  var p = PATHOF[sc];
  if (!p || noPush) { return; }
  try { if (location.protocol !== 'file:') { history.pushState({ sc: sc }, '', '/' + p); } }
  catch (e) { /* file:// 或沙箱下静默跳过 */ }
}

/* 浏览器前进/后退 */
window.addEventListener('popstate', function (e) {
  var sc = (e.state && e.state.sc) || fromPath(location.pathname);
  if (sc) { go(sc, true); }
});

/* 启动：直接输地址 / 刷新 时按路径落屏；未知路径回落默认屏并统一地址栏 */
(function initRoute() {
  var DEF = 's1';
  if (location.protocol === 'file:') { go(DEF, true); return; }   // ★ 双击打开的老用法保留
  var sc = fromPath(location.pathname);
  if (!sc) {
    sc = DEF;
    try { history.replaceState({ sc: sc }, '', '/' + PATHOF[sc]); } catch (e) {}
  }
  go(sc, true);
})();
```

实现要点（都是静默失效类，不写就会"看着做了其实没生效"）：

- `go(sc, noPush)` 要**加第二个参数**：只有用户主动切屏才 push，启动落屏与 popstate 回放**不能**再 push，
  否则后退键要按很多次才能退出（历史被自己灌满）。
- **`file://` 兜底是硬要求**：`if (location.protocol === 'file:') { go(DEF, true); return; }`。
  用户的习惯是双击打开；开发版也必须能 file:// 跑（**回归套件按 file:// 跑，全绿才说明没破坏老用法**）。
- 未知路径**不要 404 式空白**，回落默认屏 + `replaceState` 把地址栏统一，用户看到的是正常系统。
- 想加屏就改 `ROUTES` 一处；`PATHOF` 反向表由它推出，别手写两份。

### ③ macOS 启动脚本（`.command`，双击即用）

```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
PORT=8080
while lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; do PORT=$((PORT + 1)); done   # 占用则顺延
python3 serve.py "$PORT" & SRV=$!
sleep 1
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="$HOME/.drs-chrome"        # ★ 独立配置目录：不带出用户自己的书签/历史/扩展
if [ -x "$CHROME" ]; then
  "$CHROME" --new-window --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check \
            "http://localhost:$PORT/" &
else
  open "http://localhost:$PORT/"     # 回退：默认浏览器
fi
wait $SRV
```

- **`--new-window` 而不是 `--app=`**：应用模式没有地址栏，与本方案目的相反（用户明确要看到地址）。
- `--user-data-dir` 指向**独立目录** —— 这是"书签栏不出洋相"的正解（书签比地址栏更尴尬）。
- **端口占用顺延**，不要 exit 1（用户机器上 8080 常被占）。
- 全屏用 **⌃⌘F**；**Mac 的 F11 是「显示桌面」，别写**。
- ⚠️ 脚本是给 macOS 的，agent 在 Linux 上**只能 `bash -n` 校验语法 + 报明没在目标平台真跑过**，
  请用户回传终端输出。**别把"语法通过"说成"已测可用"。**

## 四、验证配方（本轮 25 项全过，照这个写）

真起服务，用真 Chrome 逐条访问 —— **必须双向核对「地址」与「落在哪个屏」**，只对一边会漏掉"地址变了但屏没变"：

```python
# 每条路由：goto(url) -> 断言 .screen.on 的 id == 期望屏；再断言当前地址 == 该路由
for path, sc in ROUTES.items():
    pg.goto(f'http://localhost:{port}/{path}')
    assert active_screen(pg) == sc
    assert pg.evaluate('location.pathname') == '/' + path

# 另加五条必测（本轮后半段全靠它们抓到真问题）
# 1) 根路径 / 落默认屏，且地址被统一成 /xzzwsjml
# 2) 乱输路径回落默认屏（不是白屏、不是 404）
# 3) 系统内点菜单切屏 -> 地址栏跟随变化（pushState 生效）
# 4) 浏览器后退 -> 回到上一屏
# 5) 页面渲染正常 + 页脚无版本号（演示版）+ 控制台无 JS 报错
```

**还要跑一遍 file:// 全套回归**（20 套）——它是"路由没破坏双击打开"的证明。
本轮结论：**路由实测 25/25 + 回归 20/20 全绿**。

## 五、交付说明要写的三件事

1. **地址表**（第二节那份），用户自己知道怎么跳页。
2. **`serve.py` 不能省的理由**（`http.server` 会 404）—— 用户换用自己的服务方式时会踩这个。
3. **现场技巧：每页可直达**，讲某一屏就直接开那条地址，省掉一路点菜单。
