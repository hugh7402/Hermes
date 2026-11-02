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

## 四、验收清单

1. 最小环境跑通，退出码 0。
2. 连跑两次，第二次静默（幂等）。
3. 目标状态一致性：如 `git rev-parse HEAD == origin/main`、`rev-list --count == 0`、产物文件存在且大小合理。
4. incident 置 `resolved`，并确认 `cron_incidents` 无残留未解决项。
5. **把修复过程写成脚本同目录的 md**（现象/根因/改了什么/下次怎么查）。
   用户下个周期才真正跑到，聊天记录里的话他到时候找不到，文件在脚本边上他一定看得到。

## 坑

- **别把 cron 里的 `command not found` 归成「没装」**：几乎总是 PATH/HOME 差异。先 `env -i` 复现，再决定是改绝对路径还是真去装。
- **别等 cron 自己跑第二次来验证**：月级任务等一个月才发现没修好，代价太大。手工最小环境跑通再交。
- **大文件已被 git 跟踪后**，历史里会留 blob（本地 `.git` 变大），但不影响后续推送；除非要缩容，不必重写历史。
- **清掉坏的未推送提交用 `git reset --soft origin/main`**：把改动收回暂存区 → 剔除不该进的文件 → 重新提交一次。
  比 `rebase -i` 逐个改安全得多，尤其自动备份这类提交本来就没有需要保留的语义。
- **别在服务起来前就宣称「已启动」**：脚本里起服务、开浏览器这类动作，顺序反了会出现「打开瞬断」，
  慢机器才复现，本地不测就交付等于埋雷。

## 支持文件

- `scripts/run_under_cron_env.sh`——用最小 PATH/HOME 跑任意脚本，复现 cron 环境。
