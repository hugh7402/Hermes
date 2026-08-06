---
name: git-backup
description: 为 Hermes 配置和 skill 设置 Git 自动备份到 GitHub/GitLab，含 git init、.gitignore、认证、cron 定时推送
tags: [备份, git, github, cron, 运维]
trigger: 当用户说"备份"、"git备份"、"自动备份"、"代码备份到GitHub"、"push到"等涉及配置备份的场景时加载
---

# Git 自动备份：Hermes 配置 + Skills + 关键文件

## 适用场景
- 安装实验性工具前备份当前配置（如 hermes-agent-self-evolution）
- 自动每日备份到 GitHub 私有仓库
- 换机/重装时快速恢复

## 备份范围

| 包含 | 排除 |
|------|------|
| config.yaml | .env（API keys） |
| skills/（含 .archive） | cache/ |
| hindsight/ | .hermes/sessions/ |
| soul.md | __pycache__ / .venv |
| proxy-skill/ | node_modules / *.lock |
| 自定义脚本 | 临时文件 /tmp |

## 快速搭建

### 1. Git 初始化

```bash
cd /opt/data
git init
git branch -m main
git remote add origin https://github.com/<user>/<repo>.git
```

### 2. .gitignore

```gitignore
# Sensitive
.env
*.env.*
credentials*
secrets*
.bailian_key*

# Large / cache
cache/
__pycache__/
*.pyc
.venv/
node_modules/
.hermes/state/
.hermes/sessions/

# System / config dirs (push declined if committed)
.cache/
.config/
.hermes/
.hermes_history
.hermes_scripts/
.learnings/
.local/
.npm/
.siyuan_extracted

# Data / user files
Obsidian Vault/
OutPut Box/
WebChat BackUp/
PikPak/
sessions/

# Large binaries
*.AppImage
*.tar.gz
*.so
*.so.*

# Temp / scripts / generated
/tmp/
*.pid
*.log
*.bak*
*.db
*.db-shm
*.db-wal
state/
memories/
memory/
plugins/
gateway/
weixin/
apps/
logs/

# Embedded git repos (must exclude or push fails)
daily_stock_analysis/
frontend-slides/
humanize-ppt/

# Lock files
*.lock
INBOX_FILES/
.DS_Store
Thumbs.db
```

### 3. 首次提交

```bash
git add config.yaml skills/ hindsight/ soul.md proxy-skill/ .gitignore
git commit -m "Initial backup: Hermes config + skills"
```

### 4. 认证方式

**HTTPS + Personal Access Token（推荐）：**
- GitHub: Settings → Developer settings → Personal access tokens → Fine-grained tokens
- 权限：Contents (read/write)
- 缓存凭据：`git config --global credential.helper store`

**SSH Key：**
```bash
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub  # 添加到 GitHub SSH keys
git remote set-url origin git@github.com:<user>/<repo>.git
```

### 5. 设置 cron 自动推送

用 `cronjob` 工具一句话：

```bash
cronjob action=create \
  schedule="5 18 * * 1,4" \
  name="auto-git-backup" \
  script="git_backup.sh" \
  no_agent=true
```

> **⚠️ script 字段只传文件名，不要传绝对路径，更不要传内联脚本内容**。cronjob 工具校验要求相对路径；调度器把文件名解析到 `/opt/data/scripts/` 目录下找文件。传绝对路径会被工具拒绝（"Script path must be relative"），传内联 `#!/bin/bash...` 内容会被当路径拼接成 `/opt/data/scripts/#!/bin/bash...` → `Script not found` 报错（2026-08-03 auto-git-backup 事故根因）。

或手动用终端写脚本：

```bash
mkdir -p /opt/data/scripts
```

脚本内容（`git-backup.sh`）：

```bash
#!/bin/bash
# 确保代理运行（中国网络环境）
bash /opt/data/proxy-skill/proxy.sh start 2>/dev/null
sleep 2

cd /opt/data
if [ -z "$(git status --porcelain)" ]; then
  exit 0  # 无变更，直接退出
fi

git add -A
git commit -m "auto backup $(date +%Y-%m-%d)"
git push 2>&1
```

> **注意**：如果推送被 GitHub 规则拒绝（`push declined due to repository rule violations`），说明 `git add -A` 带入了敏感文件。检查 `.gitignore` 是否遗漏了 `.bailian_key*`、`.config/`、`.cache/` 等目录。
> 
> 当前实际使用的 cron 是 `auto-git-backup`（周一/周四 18:05，用户 2026-07-29 改的），no_agent 模式直接跑脚本。实际脚本 `/opt/data/scripts/git_backup.sh` 逻辑：`proxy.sh start` → `git status --porcelain` 为空则静默退出（stdout 空 → cron 不投递）→ 有变更才 add/commit/push。**排查 cron 报错先看 `last_error` 字段**（`cronjob list` 或 `/opt/data/cron/jobs.json`），它直接给出失败原因（如 `Script not found: /opt/data/scripts/#!/bin/bash...` = script 字段被存成了内联内容而非文件名）。

加执行权限并测试：`chmod +x /opt/data/scripts/git-backup.sh && /opt/data/scripts/git-backup.sh`

## 坑点

- **空仓库首次推送**：`git push -u origin main` 需要先设 upstream
- **https 无交互认证**：容器环境可能弹不出用户名输入，必须用 token + credential store 或 SSH
- **.gitignore 漏了 .lock 文件**：`INBOX_FILES/workspace/.lock` 这类锁文件会导致 `git add -A` 失败
- **不要备份整个 /opt/data**：session 数据库可能很大（GB 级），只加需要的目录
- **cron script 字段只填文件名**：cronjob 工具把 `script` 解析到 `/opt/data/scripts/`（不是 `~/.hermes/scripts/`！），传绝对路径会被拒、传内联内容会报 `Script not found: /opt/data/scripts/#!/bin/bash...`。脚本本体放 `/opt/data/scripts/git_backup.sh` 并 `chmod +x`
- **⚠️ `git add -A` 会带上敏感文件和嵌入式 git 仓库**：`.bailian_key*`、`.config/rclone/rclone.conf` 等 token/key 文件会被 GitHub 规则拦截（push declined due to repository rule violations）。.gitignore 中必须显式排除 `.cache/`、`.config/`、`.hermes/`、`.local/`、`.npm/` 等 dot 目录，以及嵌入式 git 子仓库（否则推送失败）
- **⚠️ GitHub 推送需要代理**（中国网络环境）：cron 脚本中需先 `bash /opt/data/proxy-skill/proxy.sh start` 再 `git push`
- **hermes-agent-self-evolution 等实验工具装前先 push 一次**：确保有可回退点

## 恢复

```bash
git clone https://github.com/<user>/<repo>.git /opt/data
# 或从已有仓库拉更新
cd /opt/data && git pull
```
