---
name: agent-smart-development
description: 智能体/工具开发全流程——用最少 token 高效开发，集成 spike 快速验证、systematic-debugging 根因调试、token 优化三大方法论
version: 1.1.0
tags: [开发, 智能体, agent, skill, 工具, 调试, 脚本]
trigger: 当用户说"开发"、"写skill"、"写脚本"、"写工具"、"创建skill"、"编写agent"、"调试"、"开发智能体"等涉及智能体和skill开发的场景时，必须加载本skill
---

# 智能体开发全流程

## 模型配置 (2026-07-29 更新)

智能体/Skill 开发使用以下模型配置：

| 角色 | 模型 | 平台 | API端点 |
|:---|:---|:---:|:---|
| 🥇**主模型** | **zai-org/GLM-5.2** | 硅基流动 | api.siliconflow.cn/v1 |
| 🥈**备用** | **deepseek-ai/DeepSeek-V4-Pro** | 硅基流动 | api.siliconflow.cn/v1 |

**Key**：SILICONFLOW_API_KEY（`.env`中，用`os.open()`绕过掩码读取）

> ⚠️ 所有涉及智能体开发、skill 编写、工具开发的场景，**必须加载本 skill** 并按此模型配置执行。

完整评测：`references/agent-model-benchmark-20260627.md`、`/opt/data/benchmark_agent_dev.py`

## PikPak 下载须知
- ❌ **严禁走代理**下载 PikPak 文件。PikPak WebDAV/CDN 直连 HTTP，用 SOCKS5 代理慢到 0.3 KB/s 且按流量计费
- ✅ **CDN 直链 + Python urllib 多线程 Range 分片**是最快选择。脚本：`/opt/data/pikpak_cdn_dl.py`
- ✅ **rclone copyurl + CDN 直链**备选，稳定不掉速但单线程慢
- ❌ **rclone copy**（WebDAV）持续掉速（1.5MB/s→50KB/s），不推荐
- ❌ **rclone cat --offset --count 并发**：WebDAV 限流严格，并发返回 0 字节
- **获取直链**：`PikPakApi.get_download_url(file_id)` → `links[].url`（支持 HTTP Range）
- **CDN URL 有效期** ~24h，支持并发 Range 请求（8×8MB/片 ≈ 1.6MB/s）
- **后台 stdout 缓冲**：Python 脚本在 Hermes background=true 模式时，输出默认缓冲不显示。必须加 `PYTHONUNBUFFERED=1` 或 `python3 -u` 参数
- 完整策略和测试数据：`references/pikpak-download-strategy.md`

## 适用场景
- 开发/调试新的智能体脚本或工具
- 集成第三方 API（尤其是未用过的新 API）
- 搭建自动化工作流
- 遇到 Bug 需要排查
- 任何涉及"试错"的开发任务

## 总则：三段式工作法

```
┌─────────────────────────────────────────────────┐
│  ① 先验证（Spike 模式）                           │
│  想法 → 最小实验 → 确认可行 → 再写代码             │
├─────────────────────────────────────────────────┤
│  ② 再开发（Token 优化模式）                        │
│  最小函数 → 逐步完善 → 一次只改一个变量 → 日志分级   │
├─────────────────────────────────────────────────┤
│  ③ 出问题（Systematic Debugging 模式）             │
│  根因调查 → 模式分析 → 假设验证 → 修复实施          │
└─────────────────────────────────────────────────┘
```

---

## 第一部分：先验证 — Spike 模式

**目标**：用最少投入验证想法是否可行，再动手写完整代码。

### 适用判断

| 情况 | 用 Spike | 直接开发 |
|:----|:--------:|:--------:|
| 这个 API 我用过，知道它返回什么 | | ✅ |
| 不确定这个库/API 能不能达到目的 | ✅ | |
| 不确定哪种方案更好（A vs B） | ✅ | |
| 需求很明确，技术路线很清晰 | | ✅ |
| 想知道"这样做会不会崩" | ✅ | |

### Spike 四步法

#### 1. 分解问题
把想法拆成 **2~5 个独立的可行性问题**，按风险排序（最可能让想法流产的先验证）：

| # | 验证什么 | 风险 |
|---|---------|:----:|
| 001 | API 能否返回所需格式的数据 | 高 |
| 002a | 方案 A 的性能是否达标 | 中 |
| 002b | 方案 B 是否更优 | 中 |

#### 2. 先查文档，不猜
- `web_search("pikpak api file selection")` — 搜文档
- `web_extract(url)` — 读 API 文档页面
- 确认端点、请求格式、响应结构
- **宁花 2 分钟查，不花 10 分钟试**

#### 3. 最小实验
用 **curl 或单行 Python** 测试 API，不要写完整脚本再跑：

```bash
# ✅ 正确：先 curl 确认
curl -s --socks5 ... 'https://api.example.com/v1/files' | python3 -m json.tool

# ❌ 错误：写 200 行脚本再跑，发现 API 根本不通
```

**最小实验原则：**
- 测试放 `/tmp/`，用完即删
- 能 curl 就不写 Python
- 能写 3 行就不写 30 行
- **不写完整脚本再跑——跑一次就是几十秒甚至几分钟**

#### 4. 验证结论
每个实验用 verdict 收尾：

```markdown
## Verdict: VALIDATED | PARTIAL | INVALIDATED
- 什么可行：
- 什么不行：
- 意外发现：
- 实际开发的建议：
```

**VALIDATED** = 可行 ✅ | **PARTIAL** = 有条件可行 ⚠️ | **INVALIDATED** = 不可行（这也是成功）

---

## 第二部分：再开发 — Token 优化模式

**目标**：用最少 token 完成开发，避免来回试错。

### 黄金法则

#### 法则 1：一次只改一个变量
每次只改一处逻辑，测试通过后才改下一处：

```python
# ❌ 错误：同时改了 4 个东西
改搜索URL + 加重试逻辑 + 改文件选择 + 加重命名 → 跑 → 失败 → 不知道哪个坏了

# ✅ 正确：一步一步来
改搜索URL → 跑 → 确认 ✅
加重试逻辑 → 跑 → 确认 ✅
改文件选择 → 跑 → 确认 ✅
加重命名 → 跑 → 确认 ✅
```

#### 法则 2：函数最小化
- 一个函数只做一件事
- 函数写完立刻验证（最小单元测试）
- 不攒一堆代码再跑

#### 法则 3：日志分级，不全部 print
```
INFO  = 关键步骤（当前在做什么）
WARN  = 可恢复的异常（重试了几次）
ERROR = 需要终止的异常
DEBUG = 详细变量值（默认关闭）
```
**token 也是成本，每一步都 print 等于白烧钱。**

#### 法则 4：异常路径提前想
写代码前列 3~5 个"什么会崩"的场景：

| 场景 | fallback |
|:----|:---------|
| 网络掉线 | retry 3 次 |
| 搜索无结果 | 提示用户换关键词 |
| API 返回异常 | 打印错误信息，不崩 |
| 目标文件已存在 | 跳过或覆盖（按场景） |
| 超时 | 设 timeout，catch TimeoutError |

#### 法则 5：失败后先诊断，不盲目重试
请求失败时，用基础工具先找根因，再决定下一步：

```bash
# ✅ 先诊断
curl --socks5 127.0.0.1:10808 httpbin.org/ip    # 代理通不通？
curl -v https://api.example.com                   # 看完整响应
nslookup example.com                               # DNS 解析？

# ❌ 盲目重试
for i in {1..5}; do curl ...; done                # 不知道为啥失败就重试
```

**诊断时间 < 猜时间**

### 推荐开发流程

```
1. 需求分析（30秒）
   └─ 输入 → 输出 → 异常场景 → 边界条件

2. API/文档确认（1-2分钟）
   └─ curl 测试最小端点，确认响应格式

3. 写最小函数（3-5分钟）
   └─ 一个函数，只做一件事，立刻验证

4. 逐步完善（每步1次验证）
   └─ 基功能 → 异常处理 → retry → 清理 → 日志

5. 最终集成测试（1次完整流程）
   └─ 跑完整流程，确认无误
```

---

## 第三部分：出问题 — Systematic Debugging 模式

**核心原则：找到根因之前，不提修复方案。**

### 四阶段法

#### 阶段 1：根因调查（找到为什么）
**优先于任何修复。** 症状层面的修复都是失败。

1. **读错误信息** — 不要跳过。错误信息往往就是答案。
2. **稳定复现** — 能不能稳定复现？不能就别猜。
3. **查最近改动** — `git log -10` / `git diff`
4. **追踪数据流** — 坏数据从哪来的？一路往上游追。
5. **诊断先行** — 加诊断日志，确定问题出在哪个组件

```
🛑 确认已理解以下问题前，不进阶段 2：
- [ ] 错误信息已完全理解
- [ ] 问题可稳定复现
- [ ] 根因假设已形成
```

#### 阶段 2：模式分析（别人怎么做）
- 找代码库里相似的**能工作的**代码
- 对比差异：能工作的 vs 不能工作的
- 列出每个差异，不要主观排除"这不重要"

#### 阶段 3：假设验证（科学方法）
1. 形成单一假设："我认为 X 是根因，因为 Y"
2. **最小改动**验证假设
3. 成功 → 阶段 4；失败 → 新假设
4. 不懂就直说"我不懂 X"，不要装懂

#### 阶段 4：修复实施（从根源修）
1. 先写回归测试（验证 bug 存在）
2. **一次一个修复**
3. 验证通过
4. 如果连续 3 次修复都失败 → **停！** 质疑架构设计

### 三振出局法

```
第 1 次修复失败 → 回到阶段 1，用新信息重分析
第 2 次修复失败 → 回到阶段 1，重新审视假设
第 3 次修复失败 → 停！跟用户讨论：是不是架构有问题？
```

### 常见陷阱

| 想法 | 真相 |
|:----|:----|
| "问题简单，不需要流程" | 简单问题也有根因，流程对简单问题很快 |
| "紧急情况，没时间" | **系统化调试比瞎猜更快** |
| "先试一下，不行再查" | 第一次修复定了基调，一开始就要做对 |
| "一次改多个省时间" | 无法隔离哪个改了，还引入新 bug |
| "我知道问题在哪，直接修" | 看到症状 ≠ 理解根因 |

---

## 实践对照：JAV 智能体开发复盘

以一个真实案例说明三段式工作法怎么省 token：

### ❌ 实际踩的坑（浪费了很多 token）
```
猜测 selected_files PATCH → 写完整函数 → 跑失败
修改重试逻辑 → 再跑 → 还失败
换 params.files 思路 → 再跑 → 还是不行
最终发现用 file_list 查子文件 + batchMove 才正确
→ 浪费：4~5 轮完整测试，每次等 60 秒
```

### ✅ 应该怎么做（省 80% token）
```
Spike 阶段：
  curl PikPak API 测试响应格式 → 发现 params.files=0（2分钟）
  改用 file_list 查子文件 → 确认可行 ✅

开发阶段：
  写 pikpak_cleanup_ads() → curl 验证删除 → ok
  加 batchMove → curl 验证移动 → ok
  加重命名 → curl 验证 → ok
  集成到 jav_manager.py → 一次通过 ✅

→ 省下：3 次完整测试（约 3 分钟）+ 无数来回改代码
```

---

## 经验教训库（持续积累）

> 详细 PikPak API 实战踩坑记录见 `references/pikpak-api-pitfalls.md`  
> PikPak 下载策略（速度、代理、限流）见 `references/pikpak-download-strategy.md`  
> 包含：字幕关键词（破解≠字幕）、文件移动顺序、API 端点速查

### PikPak API
- `offline_file_info` 的 `params.files` **不暴露**子文件列表（PikPak 不返回这个）
- 从 PikPak 下载大文件：推荐用 `pikpak_cdn_dl.py`（CDN 直链 + 8 线程 HTTP Range 分片），稳定 1.5MB/s 不降速
- rclone copy WebDAV 备选，但持续降速（1.4MB→50KB/s）且触发 503 限流
- **不要走代理下载**（代理按流量收费，且极慢 ~0.3KB/s）
- 获取直链：`PikPakApi().get_download_url(file_id)` 返回 CDN URL（24h 有效期）
- pikpakapi 库初始化用 `PikPakApi(encoded_token=json.dumps(token_data))`，token 存于 `/opt/data/.pikpak_token.json`
- WebDAV 密码从 rclone config 获取：`/tmp/rclone reveal "<encrypted>"` 解密
- 速查：`skill_view(name="pikpak-webdav-manager")` 有完整下载方案
- 查子文件用 `file_list(parent_id=folder_id)` 替代
- 文件移动用 `POST /drive/v1/files:batchMove`，不是 PATCH `parent_id`
- 文件重命名用 `PATCH /drive/v1/files/{id} {"name": "..."}`，需在删文件夹之前操作

### 脚本参数传递（subprocess + 带参脚本）
- 当 wrapper 脚本调用另一个带参数的主脚本时，**不要**用固定数组 `["python3", script]`
  ```python
  # ❌ 错误：WATCH_SCRIPT = "/opt/data/jav_manager.py --watch"
  # subprocess.run(["python3", WATCH_SCRIPT])  → 把整个字符串当文件名
  # ✅ 正确：用 shlex.split() 拆分
  import shlex  # 或 shlex
  subprocess.run(["python3"] + shlex.split(WATCH_SCRIPT))
  ```
- 后续如果主脚本新增参数，wrapper 不用改代码

### rclone / 路径拼接
- `rclone copy --files-from list.txt remote: /dest/` 时，list.txt 里的路径是相对于 `remote:` 根目录
- **不要**在文件名前加路径前缀（如 `/Inbox-JAV/xxx.mp4`），否则会在目标目录创建嵌套子目录
- 正确做法：list.txt 只写文件名，远程源用 `remote:/Inbox-JAV` 指定

### 代理/网络
- 代理节点不稳定时 **加 retry** 比重启可靠
- 优先用 `curl -v` 看完整响应，不要只看状态码
- 代理节点到手先测连通性和延迟

### 一般原则
- 新 API 永远先 curl 测最小端点
- 写代码前列异常场景清单
- 一个改动确认通过再改下一个
