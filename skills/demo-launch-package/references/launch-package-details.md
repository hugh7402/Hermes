# 启动包实施细节（路由补丁 / 服务实现 / 验证骨架 / 踩坑）

基准项目：`/opt/data/designs/drs-demo/`（四川一体化数据资源管理系统，V2.9 起带每屏路由，17 屏）。
生成器（mac / Windows）：`make_startpack3.py`、`make_winpack.py`，均在 `/opt/data/.tmp_tests/proto/`。

## 一、路由补丁（加进 `src/app.js`）

```js
  /* ── 路由：每屏一个拼音首字母路径（http(s) 下生效，file:// 自动跳过）── */
  var ROUTES = { s1:'xzzwsjml', s1b:'sjmllb', s2:'sjmlspgl', s3:'gjgdywsh', s3b:'sjgjgd',
                 s4:'gjgdsh/djs', s4b:'gjgdsh/ybj', s4c:'qzsjk', s4d:'gjsjk',
                 s5:'lxgjrw', s5b:'mlgjzt', s6:'sjzlgzpz', s6b:'gzpzspgl',
                 s7:'zlrwgl', s7b:'rwslywgl', s7c:'sjqxjgmx', s8:'zlcxzl' };
  var ROUTES_REV = (function () { var r = {}; for (var k in ROUTES) r[ROUTES[k]] = k; return r; })();
  function screenOfPath(p) {
    var s = String(p || '').replace(/^\/+|\/+$/g, '');
    if (!s) return null;
    return ROUTES_REV[s] || (/^s[0-9]b?c?d?$/.test(s) ? s : null);   // 也允许直接写屏号
  }
  function pushRoute(sc) {
    try {
      if (location.protocol === 'file:') return;        // ⚠️ file:// 下 pushState 抛异常
      var p = '/' + (ROUTES[sc] || '');
      if (location.pathname !== p) history.pushState({ sc: sc }, '', p);
    } catch (e) {}
  }
```

接入三处：

1. `go(sc)` 改签名 `go(sc, noPush)`，函数内 `if (!noPush) pushRoute(sc);`（内部跳转也同步地址栏）。
2. 启动（`DOMContentLoaded` 里 `render()` 之后）：
   ```js
   var _sc0 = screenOfPath(location.pathname);
   if (_sc0 && META[_sc0]) { S.screen = _sc0; S.sys = META[_sc0].sys; }
   render();
   pushRoute(S.screen);      // 根路径 / 未知路径 → 统一成该屏路由
   ```
   ⚠️ `S.sys` 必须一起设，否则侧栏/顶部系统导航与屏幕不一致。
3. `window.addEventListener('popstate', function (e) { var sc = (e.state && e.state.sc) || screenOfPath(location.pathname); if (sc && META[sc]) { S.sys = META[sc].sys; go(sc, true); } });`

路由名 = 页面标题的拼音首字母（用户点名要的）。抓全屏清单：真 Chrome 里 `page.evaluate` dump `META`。

## 二、服务实现

**mac（`templates/serve-spa.py`）**：`SimpleHTTPRequestHandler(directory=ROOT)` 子类，`do_GET/do_HEAD`
先判路径是否命中文件、未命中改 `self.path='/index.html'`；`ThreadingHTTPServer(('127.0.0.1', PORT))`，
`log_message` 静默。

**Windows（`templates/serve-spa.ps1`）**：`TcpListener` 裸写；单请求单连接（`Connection: close`）；
`Content-Type` 小字典；`Cache-Control: no-store`；端口占用 +1 重试 20 次；`$reqPath -notmatch '\.\.'` 拦穿越。

PS 5.1 兼容与容错（都实际踩过）：

- 不用 `??`；三元用 `$x = if (…) {…} else {…}`。
- `Join-Path $env:ProgramFiles …` 在环境变量为空时会抛，`$ErrorActionPreference='Stop'` 下直接终止脚本
  → 先 `if ($env:ProgramFiles) { $candidates += (Join-Path …) }`。
- `$env:USERPROFILE` 可能为空 → `$homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }`。
- 打开浏览器整体包 `try/catch`，失败只提示「请手动访问」，**不能中断服务**。

## 三、验证脚本骨架

| 脚本 | 做法 | 实测 |
|---|---|---|
| `verify_routes.py`（mac） | `subprocess` 起 `serve.py` → 逐条 `goto` 断言 `screen`+`pathname` → 根路径归一 → `APP.go('s7c')` 断言地址变 → `go_back()` 断言回上一屏 → 页脚无版本号 → 无 JS 报错 | 25/25 |
| `verify_win_routes.py`（Windows） | 同上，但 `[PWSH,'-NoProfile','-NonInteractive','-File','serve.ps1','-Port','8080']`；env 补 `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT='1'` 与假 `USERPROFILE/ProgramFiles/LOCALAPPDATA` | 39/39 |
| `verify_traversal.py` | 裸 socket 发 `GET /../../../../etc/passwd HTTP/1.1`，断言无 `root:…:/bin/bash` | 2/2 |
| `verify_demo_pack.py` | 真 Chrome 查页脚无版本号、Ctrl+D 失效、标题=系统名、无 JS 报错 | 11/11 |

真 Chrome 路径：`/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell`（playwright 1.63
`executable_path=` + `--no-sandbox --disable-gpu`）。低内存机器上**并发跑两个 Chrome 回归易 `TargetClosedError` → 串行**。

## 四、踩坑记录（按发生顺序）

1. 先按「应用模式隐藏地址栏」做了，用户两轮后改主意要**显示地址栏** → 脚本里两种方式都留，说明文档写清怎么切。
2. 验证脚本用 `.foot` 取页脚，实际类名是 `.footer` → 断言前先 dump 真实类名。
3. 本机没有 `zip` 命令 → stdlib `zipfile`。
4. 首次做包时旧命名的目录留在交付目录里（用户看得见混版）→ 重出/重命名必须同时清目录与 zip。
5. `urllib` 规范化 `../` → 目录穿越测试**假通过**（报了 ❌ 其实是测试错）→ 改裸 socket。
6. 「取消演示字眼」：包名/脚本名/说明文档/配置目录名都不能带「演示」「原型」；
   连说明里「路径不要含"演示"字样」这类提醒也改写掉（用户按关键词核对）。
7. Windows 的 `serve.ps1` 在 Linux 上跑需 `pwsh` 解包 + `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1`（缺 libicu）。
   这属于本机环境，不是脚本缺陷；**别因此把 Windows 版降级成「只做语法校验」**。
8. 页面文件名用 `index.html` 让地址是干净的 `http://localhost:8080/`；
   中文文件名会变成 `%E5%9B%9B%E5%B7%9D…` 百分号转义，反而更扎眼。
