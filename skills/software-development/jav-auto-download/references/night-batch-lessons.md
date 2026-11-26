# 批量下载的坑（一次几十个番号时按这个顺序排查）

批量跑的时候，真正卡住进度的往往不是 javdb 配额，而是下面这些**自己写出来的坑**。
按严重程度排，每条都是「现象 → 机制 → 规则」。

---

## 1. 🚨 javdb 详情页会混进**别的番号**的磁链 —— 必须先过番号闸门

**症状**：搜 A 番号，选中的却是 B 番号的片源，而且会挂着 A 的文件名入库。

**机制**：javdb 搜索是模糊匹配，返回的详情页里可能同时含相邻番号的磁链条目。
实测搜 `SNOS-477` 时该页混着 `SNOS-470-LTX`（4.50GB），比 `SNOS-477` 自己的 3.50GB 大，
于是「取最大」规则**必然**选中 470。体积差得越多越容易中招，而且看不出来——
`选定:` 行只会打出一个你不认识的名字。

**规则：先按番号过滤磁链集合，再谈体积。** 番号归一化后取子串匹配，一条都对不上就中止：

```python
code_nh = code.upper().replace('-', '')
same = [m for m in mags if code_nh in m['name'].upper().replace('-', '')]
if not same:
    print(f'详情页磁链里没有一条属于 {code}，javdb 模糊匹配到了别的番号，已中止')
    return 4          # 绝不下错片
mags = same           # 之后才允许排序/取最大
```

闸门要开在**选版之前**，不能只靠事后人工核对。外层队列见到「磁链里没有一条属于」
应标成 `mismatch` 并跳过——这不是节点问题，换节点只会重复踩坑、白烧配额。

> 这条与「严禁擅自替换用户给定的番号」是同一类错误的两端：一端是我改番号，
> 另一端是站点把别的番号塞进来。两边都必须拦住。

---

## 2. 🚨 同一时刻只允许一个进程切代理

**症状**：日志大面积「代理不通，跳过」，节点轮一遍全废，但单独测每个节点又都好的。

**机制**：`prep_retry.py` / `prep_queue.py` / `switch_and_prep.py` 每个进程都会
`proxy.sh stop/start` 并改写 `reality_active.json`。两个进程同时跑，A 刚起的节点被 B 换掉，
B 的连接又被 A 打断，**两边互相制造假故障**。一个被遗忘的旧任务在后台挂一小时，
就足以让整条队列白烧配额、反复重试。

**规则**：
- 云端准备只走**一个** `prep_queue.py`，不要另开 `prep_retry.py`。
- 起队列前先 `pgrep -af 'prep_retry|prep_queue|switch_and_prep'`，把重复的停掉。
- **杀掉子进程才算真杀**：`terminal(background=true)` 外层是 bash、内层才是 python，
  `kill <bash_pid>` 只杀外壳。用 `process_manage(action='kill', session_id=...)`。
- 走**直连**的任务不受影响：rclone WebDAV 与 subtitlecat 可以和切节点任务并行，不必等。

---

## 3. 🚨 `--transfers` 不管单文件并发

**症状**：一个大文件下了很久还停在两成，以为没法救。

**机制**：`--transfers N` 是「同时下几个**文件**」。单个文件时它完全不起作用。
单文件并发由 **`--multi-thread-streams`** 控制，**默认只有 4**。

**单文件大文件的正确参数**：
```bash
rclone copy "pikpak:/Inbox-JAV/$NAME" /opt/data/PikPak/Inbox-JAV/ \
  --multi-thread-streams 16 --multi-thread-cutoff 32M \
  --transfers 4 --checkers 4 --buffer-size 32M \
  --timeout 60s --contimeout 30s --retries 20 --low-level-retries 40
```
长重试（`--retries 20 --low-level-retries 40`）是必须的：限速期只有已建立的分块在慢慢挪，
把重试次数拉高能让它扛过整个窗口，不用重下。

---

## 4. 🚨 PikPak 的限速是「时间窗口配额」，别归因到账号或单文件

**现象**：同一台机器、同一时间段，速度能从 **0.7 MB/s 跳到 50 MB/s**（实测同一批里最小
0.7、最大 50.2）。慢的时候会长时间贴在 0.01–0.35 MB/s。

**机制**：PikPak 的下载带宽按**滚动时间窗口**发放额度，额度用完就掐、过一阵自己恢复。
所以它既不是「账号被封」，也不是「这个文件有问题」——**别为它改方案**。

**由此得出的规则**：
- **绝对不要为速度去试代理。** WebDAV 只是入口：`dav.mypikpak.com` 收到 GET 会 **302** 到
  `https://dl-<hash>.mypikpak.net/download/?fid=...`，真正的字节走 CDN（实测连接的 16 个
  socket 全在 `47.79.x.x:443`，一个都没连 `:80`）。代理也照样被 302 到同一批 CDN，绕不过。
- **不要反复 kill 重开**，每次 kill 都可能丢掉已下部分（见第 9 条），而且重开不改善。
- 判据：`curl -s -o /dev/null -w '%{http_code}' -u user:pass -X PROPFIND -H 'Depth: 0' \
  http://dav.mypikpak.com/Inbox-JAV/` 返回 207 就说明通道正常，慢纯粹是配额，等。
- 交付时如实说「限速是时间窗口，扛过去会自己快起来」，不要下「账号被限」这种会被打脸的结论。

---

## 5. 🚨 离线等待时长与队列子进程超时必须成对设置

**症状**：队列在处理某条时整个进程崩掉，`subprocess.TimeoutExpired` 掀翻全部待办。

**机制**：把 `prep_dl.py` 的离线等待从 90 秒拉长到 10 分钟（见第 6 条），但外层
`prep_queue.py` 调它的 `subprocess.run(timeout=580)` 没改。580 < 600，子进程先被杀，
异常又没捕获，于是**整个队列进程退出**。

**规则**：
- 内层最长等待是 X 秒，外层超时必须 > X（留 1.5 倍余量，如等待 600 → 超时 900）。
- `subprocess.run` 的 `TimeoutExpired` **必须捕获**并当成普通失败返回，不许让它冒泡：
```python
try:
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
except subprocess.TimeoutExpired:
    class _T: returncode = 124; stdout = ''; stderr = 'TIMEOUT'
    return _T()
```
- 改任何一端的等待/超时，都要顺手检查另一端。

---

## 6. 🚨 离线等待 90 秒太短，会把大文件误判成失败并重复提交

**症状**：一部 7.77GB 的片子在多个节点上全部「选定后失败」，云端却一个文件都没有。

**机制**：`prep_dl.py` 原来 `for i in range(15): sleep(6)` = 只等 **90 秒** 就
`raise SystemExit('未见离线文件夹')`。大文件 90 秒完不成 → 判失败 → 外层当成节点故障 →
**每个节点各提交一次离线任务**，白堆一堆重复任务（见第 8 条）。

**修法（已落地）**：
- 等待改成 `range(60)` × `sleep(10)` = **10 分钟**。
- 等不到返回**退出码 3** 并打印「仍在离线中」，而不是抛异常。
- `prep_queue.py` 见到「仍在离线中」标 `offline_pending` 并**跳过本条**，不换节点、不重复提交。

---

## 7. 🚨 javdb 磁链可能全部没有体积数据

**症状**：某番号三条磁链体积全是 `0.00GB`，永远「没有 ≥2GB 的候选」。

**机制**：javdb 该页面 `data-size` 属性缺失，`get_magnets()` 返回 `size_bytes=0`。
不是番号不存在、也不是限流、也不是片子真小。

**修法（已落地）**：全部体积为 0 时兜底——优先选带 `-C` 字幕标记的那条，没有则取第一条，
体积等 PikPak 离线完成后再核实。

**但要注意**：`0.00GB / 0 个文件` 也可能是**真空磁链**（见第 8 条）。兜底选中的那条如果
离线后 `progress` 永远是 0，就是死磁链，别继续等。

---

## 8. 🚨 死磁链的判定与清理（`progress=0` 永远不动）

**判定**：`offline_list()` 里 `phase=PHASE_TYPE_RUNNING` + `progress=0` + `msg=Saving`，
等多久都不动 = 死磁链。**不要**把它当成「还在离线中」。

**诊断命令**（一次看清全部任务，比查文件系统有用）：
```python
tasks = (await c.offline_list()).get('tasks', [])
for t in tasks:
    print(t.get('created_time','')[:19], t.get('phase'),
          t.get('progress'), str(t.get('name',''))[:50], t.get('message'))
```

**死磁链的两个来源**：
- btih 只有 32 位（结构性死链，见 SKILL.md「PikPak 死种/无种磁链处理」）；
- 磁链本身是空的（`0.00GB / 0 个文件`），PikPak 照单全收然后永远不动。

**清理**：重试会在列表里堆出**几十个重复任务**（实测同一个番号堆了 8 个、另一个哈希名堆了 5 个）。
```python
bad = [t for t in tasks if t.get('progress') == 0 and t.get('phase') == 'PHASE_TYPE_RUNNING']
await c.delete_tasks([t['id'] for t in bad])
```
- `delete_to_trash()` 返回成功但 `file_list()` 里**立刻还能看到** —— 等几秒就没了，
  不要因为第一次还读到就重复删（同「PikPak 列表是最终一致的」）。
- `delete_forever([])` 传空列表会报 `Request parameter error`，先判非空。

---

## 9. 🚨 `pkill -x rclone` 会删掉 `.partial`，几 GB 进度直接归零

**症状**：杀掉 rclone 想「重开让它快一点」，重新启动后发现从零开始。

**机制**：rclone 收到信号终止时，若目标已在同目录存在半成品，会执行
`Removing failed copy` 主动删掉 `.partial`。**这不是「有 .partial 就一定能续传」**。

**规则**：
- **让 rclone 自己跑完**，慢就慢（限速会自己恢复，见第 4 条）。
- 真要停，先接受「可能从零重下」这个代价；或者用 `--partial-suffix` 指到独立后缀，
  让下次的 `copy` 不会把它当自己的残缺文件清掉。
- `pkill -x rclone` 只解决「按进程名精确匹配、不误杀自己」，**不解决丢进度**。

---

## 10. 🚨 本地库对比必须先剥掉 `@@@` 之类前缀，否则整片重下

**症状**：队列把本地明明已有的片子又拉了一遍（单部 6GB）。

**机制**：本地存档有的带前缀（`@@@MIKR-127-…mp4`），而「本地是否已有」的判断写成
`name.startswith('MIKR127')` → `@@@` 开头永远不匹配 → 当成缺失。

**规则**：比对前先剥前缀：
```python
re.sub(r'^[^A-Za-z0-9]+', '', p.name).upper().replace('-', '').startswith(code_nh)
```

**发现重复副本后怎么合并**：`@@@X` 与新下载的 `X` 大小一致时，**先看字幕挂在哪一边**——
常见是 `@@@X.srt` 有字幕、新的 `X.srt` 没有。正确顺序是
**① 把 `@@@X.srt` 复制成 `X.srt` 并校验字节一致 → ② 才删 `@@@X.mp4` 与其 `.srt`**。
反过来先删视频，字幕就成了孤儿，得重抓。

---

## 11. 🚨 字幕链接过滤必须盯「语言后缀」

**症状**：一次扫描要试二十多个链接，全是不相干语种（en/ar/th/tr…），单个详情页耗时五分钟以上。

**机制**：过滤条件写成 `re.search(r'zh|orig', x)`，而**整条路径本身就含**
`xxx.zh-cn(by transub)`，于是所有语种都被放行。

**修法（已落地）**：只认结尾的语言后缀
```python
zh = sorted({x for x in links
             if re.search(r'-(zh-CN|zh-TW|zh|orig)\.srt$', x, re.I) and len(x) > 8})
```
链接数从 26 降到 3。

---

## 12. 其它细碎但会咬人的点

- **subtitlecat 的 `000` 是常态**：搜索页、详情页、srt 三处各自重试 3 次、间隔 4s。
  经常第一次 000、重试即成功。
- **代理配置文件要备份原样**：脚本退出时会把 `reality_active.json` 回滚成 `orig`，
  若 `orig` 指向一个死节点，代理就整个废掉。收尾后主动
  `curl google/generate_204` 复核，别默认它是好的。
- **假活 sing-box**：旧实例占着 10808 时新实例报 `bind: address already in use` 起不来，
  但进程列表里还看得见一个 sing-box。判据是端口无监听 + curl 000。处理：kill 旧 PID 再 `proxy.sh start`。
- **判断「有没有字幕」之前先看搜索结果是不是搜索框回显**：搜索页会把番号印在 `<title>`、
  页头和表单 action 里，`grep -c <番号>` 命中**不等于**有结果条目。真判据是详情页链接文件名
  含该番号；精确匹配 0 个才是真没字幕。
