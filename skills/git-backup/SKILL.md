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

```
.env
*.env.*
cache/
__pycache__/
*.pyc
.venv/
node_modules/
.hermes/state/
.hermes/sessions/
/tmp/
*.pid
*.log
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
  schedule="0 2 * * *" \
  name="git-backup" \
  script="/opt/data/scripts/git-backup.sh" \
  no_agent=true
```

或手动用终端写脚本：

```bash
mkdir -p /opt/data/scripts
```

脚本内容（`git-backup.sh`）：

```bash
#!/bin/bash
cd /opt/data
git add -A
git diff --cached --quiet || git commit -m "Auto backup $(date '+%Y-%m-%d %H:%M')"
git push origin main
```

加执行权限并测试：`chmod +x /opt/data/scripts/git-backup.sh && /opt/data/scripts/git-backup.sh`

## 坑点

- **空仓库首次推送**：`git push -u origin main` 需要先设 upstream
- **https 无交互认证**：容器环境可能弹不出用户名输入，必须用 token 或 SSH
- **.gitignore 漏了 .lock 文件**：`INBOX_FILES/workspace/.lock` 这类锁文件会导致 `git add -A` 失败
- **不要备份整个 /opt/data**：session 数据库可能很大（GB 级），只加需要的目录
- **cron 脚本路径用绝对路径**：cron 环境变量少，`git` 命令前可能需加 PATH
- **hermes-agent-self-evolution 等实验工具装前先 push 一次**：确保有可回退点

## 恢复

```bash
git clone https://github.com/<user>/<repo>.git /opt/data
# 或从已有仓库拉更新
cd /opt/data && git pull
```
