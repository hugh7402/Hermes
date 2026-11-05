---
name: cron-job-reliability
title: 定时任务排障与加固
description: "Use when cron 定时任务失败/告警堆积/推送积压，或要新写改定时脚本并确认它真能在 cron 里跑。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cron, 定时任务, 排障, 最小环境, git备份, 幂等]
    related_skills: [knowledge-base-maintenance, hermes-agent]
    trigger: 用户问"XX 定时任务是不是失败了""巡检/备份怎么没跑"，或要新写/改定时脚本、定时任务连续失败、告警堆积、提交或推送积压时加载
---

# 定时任务排障与加固

## When to Use / 何时用

- 用户问「知识库月度巡检失败了？」「自动备份怎么不推了？」
- 告警堆积、同一条 incident 反复出现
- 新写或改一个 cron 脚本，交付前要确认它真能在 cron 里跑

核心认知：**cron 给你的是一个残缺的环境**——PATH 短、HOME 可能不是你以为的那个、没有你的 shell 配置。
「我手敲能跑」和「cron 能跑」是两件事，所有排障都从这一点出发。

## 一、先定位：失败记录在哪

Hermes 的 cron 证据链都在 `/opt/data/cron/`：

| 位置 | 内容 |
|---|---|
| `jobs.json` | job_id → name / schedule / script / enabled |
| `executions.db` 表 `executions` | 每次运行：status、started_at、finished_at、error |
| `executions.db` 表 `cron_incidents` | 失败聚合：failure_type、state、error、first_seen_at、output_file |
| `output/<job_id>/<时间戳>.md` | 每次运行的完整 stdout/stderr |

```python
import sqlite3
c = sqlite3.connect('/opt/data/cron/executions.db')
for row in c.execute("SELECT job_id,status,started_at,substr(error,1,80) "
                     "FROM executions ORDER BY rowid DESC LIMIT 20"):
    print(row)
for row in c.execute("SELECT job_id,failure_type,state,substr(error,1,160) FROM cron_incidents "
                     "WHERE state NOT IN ('resolved','closed') ORDER BY first_seen_at DESC"):
    print(row)
```

- `failure_type` 区分 `script` / `delivery` / `rate_limit`——先看类型再查内容，别把所有失败都当脚本问题。
- 🚨 **修好后要把 incident 置 `resolved`**：`UPDATE cron_incidents SET state='resolved', closed_at=? WHERE job_id=? AND state NOT IN ('resolved','closed')`。
  不置的话告警一直挂着——月级任务要挂满一整月，用户会以为没修。
- 🚨 **读 `jobs.json` 只挑字段打印**。里面可能塞着上一次失败的完整 stderr（几 MB），
  `json.dumps` 整份下去会把终端输出炸成几百万字符，把真正要看的信息埋掉。

## 二、复现：用最小环境跑，别用登录 shell

```bash
env -i PATH=/usr/bin:/bin HOME=<cron 的 HOME> /bin/bash /path/to/script.sh
echo "退出码 $?"
```

或用 `scripts/run_under_cron_env.sh <脚本>`。这一步能把「手敲能过」的假通过全部挤出来。

由此得出三条硬规则：

1. **解释器写绝对路径**。`/opt/data/.venv/bin/python3` 这类路径不依赖 PATH。
   不要指望 `uv` / `pyenv` / `nvm` / `conda` 里的东西——它们只在你登录 shell 的 PATH 里。
   venv 里已经装好的包（pyyaml / feedparser / requests 等）直接用 venv 解释器跑，别引第三方运行器。
2. **git 的身份和凭据必须在仓库级配置**，不能靠 `~/.gitconfig` / `~/.git-credentials`（HOME 不同就读不到）：
   ```bash
   git -C <repo> config user.name  "<name>"
   git -C <repo> config user.email "<email>"
   git -C <repo> config credential.helper 'store --file=/abs/path/.git-credentials'
   ```
   缺了分别报 `fatal: unable to auto-detect email address` 和
   `fatal: could not read Username for 'https://github.com'`。
   **`store` 那行必须写绝对路径**——默认的 `store` 会去 `$HOME` 找 `.git-credentials`，照样读不到。
3. **一次把 PATH、HOME、身份、凭据四样全过一遍**。这些缺失会层层套：修掉第一个才暴露第二个，
   修一层验一层会把排查轮次拖成三四倍。

验证通路的单条命令：`env -i PATH=/usr/bin:/bin HOME=… git -C <repo> ls-remote --heads origin main`
——能读到远端引用就说明身份和凭据都通了。

## 三、加固：脚本本身要防的四件事

1. **早退条件要完整**。`if [ -z "$(git status --porcelain)" ]; then exit 0; fi` 在
   「工作区干净但还有未推送提交」时会**永久跳过推送**，积压越滚越大且没人察觉。
   改成同时看：
   ```bash
   DIRTY="$(git status --porcelain)"
   AHEAD="$(git rev-list --count origin/main..HEAD)"
   [ -z "$DIRTY" ] && [ "$AHEAD" -eq 0 ] && exit 0
   ```
2. **先校验再产生副作用**。往远端推之前的那次 commit 要先做体积/白名单检查：
   - 扫暂存区，单文件超阈值（90MB 起，给托管平台 100MB 硬限留余量）就 `git restore --staged` 剔除并打印清单；
   - 不该进仓库的目录（浏览器/语言运行时、工具安装目录、临时备份目录）若被重新跟踪，`git rm -r --cached` 掉（文件不动）。
   这套闸能挡住「被平台拒收 → commit 已落地 → 越积越多」的死循环。
3. **幂等**。无变更时输出必须为空——cron 靠空输出决定不投递，脏输出会天天骚扰用户。
   同一状态连跑两次，第二次必须静默。
4. **失败要留可诊断信息**：退出码、失败阶段、三条最可能的排查命令。别一句 `exit $?` 带过。

## 四、看门狗：给常驻服务加自动拉起

守护一个本地服务（记忆库、代理、队列进程）不要靠 Hermes 的 gateway hook，用 cron 看门狗。
两者区别很实际：**hook 只在有人对话时才触发**，用户一晚上不说话、服务又挂了，hook 根本不醒；
**cron 是准点跑的**，跟有没有对话无关。hook 可以留着当第二道保险，但不能当唯一的一道。

标准形态（`no_agent=True`，不经模型，零 token 成本）：

```bash
#!/bin/bash
set -u
probe() { curl -s -m 5 --noproxy '*' "http://127.0.0.1:9177/health" 2>/dev/null | grep -q '"status":"healthy"'; }

probe && exit 0                    # ① 健康 → stdout 完全为空，cron 不投递任何消息
bash <启动脚本>                     # ② 不健康 → 拉起
for i in $(seq 1 18); do           # ③ 轮询复核，冷启动常要一分多钟，别只 sleep 一次
  sleep 5
  probe && { echo "✅ 已自动拉起（$(date '+%m-%d %H:%M')）"; exit 0; }
done
echo "⚠️ 拉起失败，需人工介入。日志：$LOG"
exit 1
```

要点：

- **只有异常时才输出**。健康时 stdout 必须为空——`no_agent` 模式把 stdout 原样投递，空输出等于不打扰。
  输出一句「一切正常」等于每天骚扰用户几十次。
- **`script` 参数只写文件名**，相对 `$HERMES_HOME/scripts/`。写绝对路径会被拒：
  `Script path must be relative to /opt/data/scripts/`。文件得是真实文件，不能是符号链接。
- **拉起脚本自身要有「已在跑」守卫**，否则看门狗和手动启动会拉起重复进程。
  守卫别用 `pgrep -f "<模块名> --参数"`——真实 argv 往往和模块名不同（如进程名是 `bin/hindsight-api` 而你以为在跑 `hindsight_api.main`），
  这个 pattern 永远匹配不上，守卫形同虚设。**直接探端口/健康接口**最可靠。
- 频率按恢复代价定：常驻服务 10 分钟级就够，别做成 1 分钟。

## 五、验收清单

1. 最小环境跑通，退出码 0。
2. 连跑两次，第二次静默（幂等）。
3. 目标状态一致性：如 `git rev-parse HEAD == origin/main`、`rev-list --count == 0`、产物文件存在且大小合理。
4. incident 置 `resolved`，并确认 `cron_incidents` 无残留未解决项。
5. **把修复过程写成脚本同目录的 md**（现象/根因/改了什么/下次怎么查）。
   用户下个周期才真正跑到，聊天记录里的话他到时候找不到，文件在脚本边上他一定看得到。

## 坑

- **优化前先数一遍：哪些任务真的调模型**。别拿一个微基准（“某模型关思考后从 202s 降到 4.6s”）外推到全部定时任务。
  实际点一遍 `jobs.json`：标了 `no_agent` 或带 `script` 的 job **全程不碰模型**（纯脚本），真正的重活（OCR/解析/摘要标签）往往在脚本内另起 API 调用、用的是关推理的别名。
  结果是“关思考”能影响的常常只有“写通知文字”那一小段，省的金额是个位数元。
  **先枚举构成、再算钱、再提方案；先提方案再核对，就会得出一个要当面推翻的建议。**
- **「装了自动修复机制」不等于它在工作**。验证方式是**看它有没有实际触发过**，不是看配置文件在不在：
  日志里只有一条手动测试记录、之后再无新增，就是这个机制从未生效。
  Hermes 的 gateway hook 只在 gateway 启动时加载，因此「先起 gateway、后装 hook」= hook 永远不会被认。
  凡是这类延迟加载的机制，装完必须重启宿主进程，并且重启后回查日志确认它真的跑了。
- **重启后验证「真的换进程了」要看 worker，不是看外层 wrapper**。用 `ps aux | grep main-wrapper.sh gateway`
  找到的那个 PID 是 s6 的监督进程，**设计上就永不重启**，拿它当判据会得出「重启失败」的错误结论（本轮就因此向用户误报过一次）。
  正确判据二选一：`hermes gateway status` 报的 PID；或 `ps --forest` 看 `s6-supervise gateway-default` 的子进程。
  该 PID 变了、启动时间变成刚刚，才算重启成功。
- **`s6-svc` 不在默认 PATH 里**，脚本里写裸命令名会 `command not found`（退出码 127）；要写绝对路径 `/command/s6-svc`，并加一道 `[ -x ]` 守卫 + 回退到 `hermes gateway restart`。
- **不能从 gateway 进程内部重启 gateway**：Hermes 会直接拦下并提示「SIGTERM 会先杀掉这条命令，请从运行 gateway 之外的独立 shell 执行」。
  正确做法是把命令交给用户在他自己的终端里执行；硬要自动化就排一个延迟几十秒的**已脱离**后台任务
  （`s6-svc -r` 只是往控制管道写指令就返回，真正动手的是 s6，不会被 SIGTERM 带走）。
  排完一定要回查 `ps` 确认动作真的发生了——不确认就会像本轮一样，用户以为重启了、你以为重启了，实际一直没动。
- **别把 cron 里的 `command not found` 归成「没装」**：几乎总是 PATH/HOME 差异。先 `env -i` 复现，再决定是改绝对路径还是真去装。
- **别等 cron 自己跑第二次来验证**：月级任务等一个月才发现没修好，代价太大。手工最小环境跑通再交。
- **大文件已被 git 跟踪后**，历史里会留 blob（本地 `.git` 变大），但不影响后续推送；除非要缩容，不必重写历史。
- **清掉坏的未推送提交用 `git reset --soft origin/main`**：把改动收回暂存区 → 剔除不该进的文件 → 重新提交一次。
  比 `rebase -i` 逐个改安全得多，尤其自动备份这类提交本来就没有需要保留的语义。
- **别在服务起来前就宣称「已启动」**：脚本里起服务、开浏览器这类动作，顺序反了会出现「打开瞬断」，
  慢机器才复现，本地不测就交付等于埋雷。

## 支持文件

- `scripts/run_under_cron_env.sh`——用最小 PATH/HOME 跑任意脚本，复现 cron 环境。
