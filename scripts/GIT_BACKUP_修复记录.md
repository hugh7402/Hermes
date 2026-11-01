# git_backup.sh 修复记录（2026-11-01）

## 当时的现象
- `auto-git-backup` 从 2026-10-12 起连续 6 次失败，最后一次 10-29。
- 报错：`remote: error: File ... chrome is 257.28 MB; this exceeds GitHub's file size limit of 100.00 MB`
  `! [remote rejected] main -> main (pre-receive hook declined)`
- 推送被拒后脚本照样 `commit`，所以未推送的提交越积越多。

## 根因（三个，叠在一起）
1. **大文件被提交**：`chrome/`（396MB 的 headless shell）、`installs/`（1.8G，含 257MB chromium 和 35MB uv）、
   `tools/`（187M 二进制）都在 git 跟踪范围内。
2. **git 身份只配在全局**：`user.name` / `user.email` 在 `/opt/data/home/.gitconfig`。
   cron 跑的时候 HOME 不是这个目录 → `fatal: unable to auto-detect email address`。
3. **凭据只配在全局**：`credential.helper = store`，靠 `$HOME/.git-credentials`。
   同样因为 HOME 不同 → `fatal: could not read Username for 'https://github.com'`。
   注意：前两者不修的话，只有第 1 条会暴露出来；修完第 1 条才会碰到 2 和 3。

另有一个脚本逻辑缺陷：第 4 个问题——工作区干净但 `origin/main..HEAD` 有积压提交时，
脚本的「无变更就退出」会直接 `exit 0`，永远不推送。

## 改了什么
1. `/opt/data/.gitignore` 追加：`chrome/`、`installs/`、`tools/`、`*.part`、`.kb_backup/`
2. `git rm -r --cached chrome installs tools .kb_backup`（只脱离索引，文件不删）
3. 仓库级身份：
   ```
   git config user.name "hugh7402"
   git config user.email "shaolei7402@163.com"
   ```
4. 仓库级凭据（关键，写死路径就不受 HOME 影响）：
   ```
   git config credential.helper 'store --file=/opt/data/home/.git-credentials'
   ```
5. 脚本加两道闸：
   - 提交前扫暂存区，单文件 >90MB 自动 `restore --staged` 剔除并打印告警
   - 大目录若被重新跟踪，自动 `rm --cached`
6. 早退条件改成「工作区干净 **且** 无待推送提交」才退出

## 怎么验（务必用最小环境，别用登录 shell）
```bash
env -i PATH=/usr/bin:/bin:/usr/local/bin HOME=/opt/data /bin/bash /opt/data/scripts/git_backup.sh
echo "退出码 $?"
git rev-list --count origin/main..HEAD   # 必须是 0
```
连跑两次，第二次输出应为空（幂等）。

## 现在的基线（2026-11-01）
- 远端：`1070663`
- 跟踪文件 1524 个，最大的单个文件已 < 10MB
- `.git` 本地 484M（历史里还留着那两个大 blob，不影响推送；要彻底缩容得重写历史，没必要）

## 下次再遇到推送失败先看这几处
```bash
git config user.email                                    # 应为 shaolei7402@163.com
git config credential.helper                              # 应带 --file=...
git ls-files -z | xargs -0 ls -la | awk '$5>50000000'    # 有没有 >50MB 的
bash /opt/data/proxy-skill/proxy.sh status               # 代理通不通
```
