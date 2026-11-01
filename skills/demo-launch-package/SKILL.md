---
name: demo-launch-package
description: "Use when 打包本机演示启动包（mac/Windows 双平台）。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [启动包, 演示包, 本地服务, 单页回退, pushState路由, Windows, macOS, PowerShell, 打包交付]
    trigger: 用户说"做个启动包""演示包""演示时不想让专家看到原型地址""地址栏显示 localhost""每页加个后缀/路由""出个 Windows 版 / mac 版""带版本号"，或要把 HTML 原型/前端产物包成现场可双击运行的演示环境时加载
---

# 本机演示启动包（把 Web 产物包成「像已部署系统」）

## 何时用

用户要在评审/汇报现场演示一个 Web 原型或前端产物，但地址栏不能露
`file://…/某某原型_V2.9.html` 这种马脚，也不方便现场敲命令行。
产物形态 = **原始 HTML + 一个本地服务 + 一个双击启动脚本 + 一份使用说明**。

本 skill 管「打包与演示环境」这一层；原型本身怎么做（单文件自包含、jsdom/真 Chrome 验证、
WeasyPrint 静态出图的坑）看 `ui-prototype` 与 `china-gov-ui-standards`。

## 一、四条硬要求（用户逐轮定下来的，别自行发挥）

1. **每屏一个 URL**，地址 = `http://localhost:8080/<该页拼音首字母>`（如 `/xzzwsjml` 新增政务数据目录、
   `/sjqxjgmx` 数据清洗结果明细）；同名子视图用二级路径（`/gjgdsh/djs` 待技术审核、`/gjgdsh/ybj` 已办结）。
   屏内导航用 `history.pushState` 改地址不刷新，启动时按 `location.pathname` 定位屏幕、
   `popstate` 接前进/后退。
   ⚠️ **`file://` 下 `pushState` 会抛异常 → 必须 try/catch 兜住**（协议为 `file:` 直接跳过），
   这样同一份 HTML 双击打开也照常用。

### 🚨 地址栏形态是这套交付的第一验收项（用户原话："启动包最重要的就是要模拟地址栏"）

| 时刻 | 地址栏必须是 |
|---|---|
| 双击启动后 | `http://localhost:8080/`　**就是个斜杠，不带任何参数** |
| 点任意菜单 | `http://localhost:8080/sjqxjgmx` 这样 |
| 地址栏直接输路由回车 | 停在该路由并落到对应屏 |
| 浏览器后退 | 回上一屏，地址同步 |

由此得出两条硬规则：

- **根路径不得被改写。** 启动引导里"未知/根路径回落默认屏"只能改**屏幕状态**，不许 `pushState`/`replaceState`
  把地址改成默认屏路由（否则一打开就是 `/xzzwsjml`，用户直接判不合格）。正确写法：仅当 `screenOfPath(pathname)`
  命中有效路由时才 `pushRoute`；否则 `render()` 后把带 query/未知路径的地址 `replaceState` 成 `'/'`：
  ```js
  var sc0 = screenOfPath(location.pathname);
  if (sc0 && META[sc0]) { S.screen = sc0; S.sys = META[sc0].sys; render(); pushRoute(S.screen); }
  else {
    render();
    try { if (location.protocol !== 'file:' && (location.pathname !== '/' || location.search))
            history.replaceState({ sc: S.screen }, '', '/'); } catch (e) {}
  }
  ```
- **不许往打开地址上挂任何 query 参数**（下面第二节的 `?t=` 反模式说得更细）。
2. **地址栏要显示**（不是应用模式）：浏览器用**普通窗口** `--new-window`。
   要隐藏就改 `--app=`、要全屏改 `--kiosk=`——**两种都写进使用说明让用户自己切**（用户会改主意）。
3. **独立浏览器配置目录**（`~/.<app>-chrome` / `%USERPROFILE%\.<app>-chrome`）：
   否则会带出用户日常的书签、历史、扩展（真实事故：演示前截图里露了用户两条个人书签）。
4. **界面里不留版本号**：版本只出现在**包名、使用说明、窗口标题**；页面页脚要干净，
   `Ctrl+D` 调试开关与 `APP.VERSION` 要中性化——专家盯页脚就能看出迭代痕迹。
   包里也**不要出现「演示」「原型」字样**（包名/脚本名/说明文档/配置目录名都算），
   用户会按关键词逐字核对。

## 二、服务端必须做「单页回退」

`python3 -m http.server` 遇到 `/sjqxjgmx` 直接 404，页面根本打不开——**这是最容易漏的一步**。
未命中文件的路径一律返回 `index.html`，路由才能直接访问与刷新。

| 平台 | 现成实现 | 要点 |
|---|---|---|
| macOS / Linux | `templates/serve-spa.py`（标准库） | `SimpleHTTPRequestHandler(directory=ROOT)` 子类，`do_GET/do_HEAD` 先判命中否则改 `self.path='/index.html'` |
| Windows | `templates/serve-spa.ps1`（无依赖） | **`TcpListener` 裸写 HTTP/1.1**；端口占用自动 +1 |

⚠️ **Windows 上不要用 Python**（通常没装），也**不要用 `HttpListener`**——后者在不少机器上要
管理员权限或 `netsh http add urlacl`，现场会翻车。两个服务都只监听回环地址，
且都拦 `..` 目录穿越（`$reqPath -notmatch '\.\.'`）。

### 🚨 服务端必须禁缓存，否则用户会说「启动包没更新」

症状：包内 `index.html` 已经换掉（MD5 与交付版相等），用户双击打开看到的还是**上一版页面**。
根因是浏览器缓存，两个因素叠加：服务端响应**不带任何 `Cache-Control`**（`SimpleHTTPRequestHandler` 默认没有），
而启动脚本用的**持久化浏览器配置目录**（`--user-data-dir=~/.<app>-chrome`，第一节硬要求 3）把磁盘缓存跨次保留下来 →
`http://localhost:8080/` 直接命中旧缓存。**别先怀疑包打错了，先查缓存这条。**

三件事一起做（缺一件都可能复现）：

1. 服务端对所有响应强制禁缓存 —— 覆写 `end_headers()`，别只改 `do_GET`（单页回退的内层响应也要覆盖到）：
   ```python
   def end_headers(self):
       self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
       self.send_header('Pragma', 'no-cache')
       self.send_header('Expires', '0')
       super().end_headers()
   ```
2. 🚨 **不要用 `?t=<时间戳>` 之类的一次性参数来防缓存**——那会让地址栏变成
   `http://localhost:8080/?t=1792475887`，用户一眼判不合格（地址栏是这套交付的验收重点）。
   禁缓存只靠上面第 1 条的响应头就足够：`no-store` 已让浏览器不落盘缓存，启动脚本打开
   **干净的** `URL="http://localhost:$PORT/"`（PowerShell 同理 `$url = "http://localhost:$Port/"`）。
   真要双保险，靠第 3 条的指纹打印去核对版本，别动 URL。
3. 启动脚本**打印版本指纹**：`index.html` 的字节数、MD5、修改时间。
   macOS：`md5 -q index.html`（回落 `md5sum`）；Windows/PowerShell：`(Get-FileHash -Algorithm MD5 -Path $index).Hash.ToLower()`
   + `(Get-Item $index).Length` + `.LastWriteTime`（`End_Headers`/响应头不带指纹打印之外的东西）。
   用户一句「好像是旧的」用这个指纹当场就能判定，省掉一整轮扯皮。
   另：`serve.ps1` 自己写的 HTTP 循环要按请求方法分流，**HEAD 只发头不发正文**（`$isHead` 判一下即可）。
4. 使用说明 FAQ 补一行：「页面内容看起来和上一版一样 → 先核对终端打印的版本指纹；仍不对就 ⌃C 关掉重开，端口会自动顺延」。

排查顺序：包内 `index.html` MD5 → 交付目录 HTML MD5 → 两者是否相等 → 再比字节数。
**同一构建的多份副本字节数应当一致；不一致才是真打错包，一致就是缓存。**

## 三、启动脚本与编码（不处理就是一堆乱码）

| 文件 | 编码 | 原因 |
|---|---|---|
| `启动.bat` | **GBK + CRLF**，首行 `chcp 936 >nul` | 中文 Windows 控制台默认 936；写成 UTF-8 必乱码 |
| `serve.ps1` | **UTF-8 带 BOM** | PowerShell 5.1 读无 BOM 的 UTF-8 按 ANSI 解析，中文注释/输出全乱 |
| `启动.command` / `启动.sh` | UTF-8 | macOS 终端默认 UTF-8 |
| `index.html` / `使用说明.md` | UTF-8 | — |

- mac：`templates/launch-mac.command`——找空端口（`lsof -nP -iTCP:$PORT -sTCP:LISTEN` 循环 +1）
  → `python3 serve.py $PORT &` + `trap 'kill $SRV' EXIT INT TERM` → `sleep 1` → Chrome 开窗 → `wait`。
  无 python3 回落 `file://`，无 Chrome 回落 `open`。
- Windows：`templates/launch-windows.bat`——校验同目录 `index.html`/`serve.ps1`、`where powershell` 存在，
  再**前台**跑 `powershell -NoProfile -ExecutionPolicy Bypass -File serve.ps1 -Port 8080`（Ctrl+C 即停）。
- 使用说明必须覆盖：双击被 Gatekeeper / SmartScreen / 「解除锁定」拦住的三种处理，
  结束方式（先关浏览器再 ⌃C / Ctrl+C），输入法、通知、缩放、别开 F12/⌥⌘I。

## 四、包命名与交付（用户明确要求）

```
{系统名}-启动包_{mac版|Windows版}_{Vx.y}
```

- **版本号从交付 HTML 文件名自动取**（`SRC.stem.split('_')[-1]`），主程序升版自动跟随，不手写。
- 两个平台包内的 `index.html` 必须**字节相同**（可互换）→ 交付前 `md5sum` 两个文件核对。
- **主程序一升版（哪怕只改了路由一行），两个平台必须同时重出、一起交付**——只出一个平台、
  或让用户手上混着新旧两个包，会被当场指出「两个不一致」，等于返工。
- 重命名/重出时必须**同时删掉旧命名的目录与 zip**（不留混版；用户看交付目录）。
- 打包用 stdlib `zipfile`（本机常无 `zip` 命令），压成 `{包名}.zip`，目录名与 zip 同名。
- 🚨 **打包后逐个成员读回校验**——只 `ls` 源目录不算验证：用 `zipfile` 打开产物、逐成员算 MD5 打印出来，重点看
  ① 包内 `index.html` 与交付版 HTML 相等；② `启动.command` 与 `启动.sh` **必须同 MD5**（后者是前者的复制品，
  复制那步被中断/跳过就会留旧副本，而源目录看上去完全正常）；③ `.command`/`.sh` 的 mode 读出是 `755`。
- 微信交付：`MEDIA:/绝对路径/xxx.zip`，两个平台各发一个，并在正文里用表格说明包内文件与差异。

## 五、验证（能真跑的都要真跑，别只做语法校验）

1. **路由与地址栏**：起服务 → 真 Chrome 先 `goto('http://localhost:8080/')`，断言 `location.pathname === '/'`
   （**不是**被归一成默认屏路由），再逐条 `goto('<route>')` 断言 `window.APP.screen` 与 `location.pathname`
   双向一致；再断言切屏改地址、`go_back()` 回上一屏、页脚无版本号、无 JS 报错。
   **两个平台的服务各跑一遍同一套断言**——mac 的 `serve.py` 与 Windows 的 `serve.ps1` 都能在 Linux 上真跑，
   行为必须完全一致，用户会拿两边对照。
2. **Windows 服务在本机（Linux）也能真跑**：拉 PowerShell 7 linux-x64 解包即可执行 `serve.ps1`
   （缺 libicu 时补 `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1`），再用真 Chrome 打 HTTP 验证。
   纯语法解析用 `[System.Management.Automation.Language.Parser]::ParseFile()`。
   env 里要给假 `USERPROFILE/ProgramFiles/LOCALAPPDATA`，并确认脚本对缺失环境变量是容错的。
3. **目录穿越用裸 socket** 发原始 `GET /../../../../etc/passwd`，断言返回体无 `root:…:/bin/bash`。
   ⚠️ `urllib` 会在客户端把 `../` 规范化掉——用它测会**假通过**（本次白报一个 ❌）。
4. 回归：改动只影响打包层时，也要跑原型的全套回归（`file://` 方式），确认双击打开的老用法没被路由破坏。
5. **禁缓存要实测响应头**，别只读代码：
   `curl -sS -o /dev/null -D - --noproxy '*' http://127.0.0.1:<端口>/` 与任一 SPA 路由，
   断言两者都带 `Cache-Control: no-store`。**`--noproxy '*'` 必加**——本机代理会把回环请求也拦走、白得一个 000。
6. 交付说明里写**「老实话」**：本机无法真跑的部分（Windows 的 Chrome 路径探测、`.bat` 控制台、
   SmartScreen 提示、真 macOS 的 Gatekeeper）要讲明，并请用户首次报错时回传窗口文字。

## 六、可选增强（写进说明，不默认做）

- `--app=` / `--kiosk=` 隐藏地址栏或全屏。
- 伪域名：hosts 加 `127.0.0.1 drs.sc.gov.cn` → 地址形如 `http://drs.sc.gov.cn:8080/sjqxjgmx`；
  想去掉端口用 80（需 sudo/管理员）。⚠️ 提醒：http + 域名会显示「不安全」，纯 localhost 反而不显示。
- 内网机器：`index.html` + 服务脚本丢给 nginx 用 IP 访问效果最好。

## 支持文件

- `references/launch-package-details.md`——路由补丁完整代码、两个服务实现说明、验证脚本骨架、逐轮踩坑记录。
- `templates/serve-spa.py` / `templates/serve-spa.ps1`——mac / Windows 的单页回退服务。
- `templates/launch-mac.command` / `templates/launch-windows.bat`——两个平台的启动入口。
