# Hindsight daemon recovery — PG 起不来 / 卡死完整实录（2026-08-17）

## Symptom
daemon 卡在日志 `Starting embedded PostgreSQL (name=hindsight-embed-hermes, port=auto)...` 之后无任何输出；进程 60-70% CPU 空转但 TIME 不再增长；`ps aux | grep postgres` 为 0；`/health` 无响应。**不是死循环，是嵌入式 postgres 二进制根本加载不起来**，pg0 一直干等。

## Root cause chain
1. pg0 的 postgres 18.1 二进制链接 `libicuuc.so.70`；Debian 13 (trixie) 只提供 ICU 76 → `error while loading shared libraries: libicuuc.so.70: cannot open shared object file`。
2. 补库后（当时手动 LD_LIBRARY_PATH 启动）：缺 PG 标准目录 → 逐级报 `could not open directory "pg_logical/snapshots"` → `"pg_logical/mappings"` → `"pg_notify"` 等，WAL 恢复/checkpoint 失败。
3. 目录补齐后 postgres 正常启动，`database system is ready to accept connections`，**数据完好（无需删实例）**。

## 修复步骤

### 1. 补齐 PG 标准目录（幂等，无损）
```bash
D=/opt/data/.pg0/instances/hindsight-embed-hermes/data
for d in pg_commit_ts pg_dynshmem pg_notify pg_replslot pg_serial pg_snapshots pg_stat_tmp pg_tblspc pg_twophase pg_logical/snapshots pg_logical/mappings; do
  [ -d "$D/$d" ] || mkdir -p "$D/$d"
done
chown -R hermes:hermes "$D"
```

### 2. 装 libicu70（无 root，Debian 系没有 ICU 70；Ubuntu jammy 有）
```bash
curl -sL -o /tmp/libicu70.deb "https://archive.ubuntu.com/ubuntu/pool/main/i/icu/libicu70_70.1-2ubuntu1_amd64.deb"
dpkg-deb -x /tmp/libicu70.deb /opt/data/.pg0/icu70/
```

### 3. postgres wrapper（持久修复，任何启动器拉起都生效）
`/opt/data/.pg0/installation/18.1.0/bin/postgres` 改为 wrapper：
```bash
#!/bin/bash
export LD_LIBRARY_PATH=/opt/data/.pg0/icu70/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
exec /opt/data/.pg0/installation/18.1.0/bin/postgres.real "$@"
```
- 原标准 postgres 18.1 二进制改名 `postgres.real`。
- **wrapper 里不要用 `exec -a postgres`**——postgres 需要可解析的 argv[0] 路径，否则 `FATAL: postgres: could not locate my own executable path`。普通 exec 即可（实测 pg_ctl 版本检查通过、完整启动成功）。
- 若原 postgres 二进制丢失：标准版从 theseus-rs 重新下载（EDB `get.enterprisedb.com` 的 URL 会 403；GitHub API 在代理 IP 上常被 rate-limit，用 HTML 页面 `github.com/theseus-rs/postgresql-binaries/releases` 找 asset）：
  `https://github.com/theseus-rs/postgresql-binaries/releases/download/18.1.0/postgresql-18.1.0-x86_64-unknown-linux-gnu.tar.gz`
  注意：**不要**用 `/opt/data/.cache/uv/.../pg0/bin/pg0` 冒充——那是 pg0 定制版（`pg0 0.15.1`，busybox 式多调用），pg_ctl 版本检查会拒绝。
- 验证（不带任何手动 LD_LIBRARY_PATH）：
  `pg_ctl -D <data> -l /tmp/pg.log -o "-p 54329 -k /tmp" start && pg_isready -p 54329 -h /tmp`

### 4. 手动启动 daemon —— 三个必设环境
```bash
export HOME=/opt/data                                     # 否则 pg0 在 /opt/data/home/.pg0 分裂数据（红线）
export HINDSIGHT_API_DATABASE_URL=pg0://hindsight-embed-hermes   # 默认实例名是 hindsight（空实例！）
unset https_proxy http_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY  # socksio 未装，SOCKS 变量让 LiteLLM 静默挂掉
set -a; source /opt/data/.hindsight/profiles/hermes.env; set +a   # LLM key/base_url
```
- **用前台模式** `hindsight-api --idle-timeout 300 --port 9177`（不要 `--daemon`）配 `setsid nohup ... &`——`--daemon` 会 fork 出孤儿 child 占住 9177，后续启动报 `address already in use`（症状：日志 `Application startup complete.` 后紧跟 bind 失败）。
- 二进制路径：`/opt/data/.cache/uv/archive-v0/UvuKov5JptV1YgV0DscNQ/bin/hindsight-api`（uvx 每次解析会重装 229 包，直接用已缓存二进制更快）。
- 固化脚本：`/opt/data/scripts/hindsight_start.sh`（三设环境 + 前台 setsid + health 检查）。

### 5. 验证
- `curl http://127.0.0.1:9177/health` → `{"status":"healthy","database":"connected",...}`
- `ps aux | grep postgres` → 数据目录必须是 `instances/hindsight-embed-hermes/data`（不是 `instances/hindsight`）
- `hindsight_recall` 能返回真实记忆 = 端到端 OK

## 过程踩坑
- **pkill -f 会匹配到自己的 shell**（命令字符串含模式）→ 自杀。用 `ps aux | grep X | awk '{print $2}' | xargs -r kill -9` 或精确模式。
- `write_file` 覆盖 `bin/postgres` 用 rename 语义，会断掉原二进制的硬链接 → 原文件不可恢复时从 theseus-rs 重下（见上）。
- 数据目录误建在 `/opt/data/home/.pg0`（HOME 错）后：kill 残留 postgres → `rm -rf /opt/data/home/.pg0 /opt/data/home/.hindsight`，真数据不受影响。
- daemon 优雅关闭不会带走 postgres 子进程 → 杀 daemon 后必须查杀孤儿 postgres（`ps aux | grep postgres`）。

## 补充：supervisor 机制 & 诊断技巧（同会话后半段）
- **daemon 的 supervisor = Hermes dashboard**（`ps -o ppid= -p <daemon_pid>` → dashboard/hermes 进程）。dashboard 在 9177 无服务时会反复自动重拉 daemon，拉起的实例环境正确（HOME=/opt/data、实例 hindsight-embed-hermes）。**恢复顺序：杀光所有 daemon/postgres → 什么都不做，等 dashboard 重拉（40-60s 初始化）→ /health 转 healthy**。手动拉起会与 dashboard 的重拉竞争：dashboard 在 9177 未服务前会再拉一个，多个实例互相 bind 失败、日志里只见 `Application startup complete.` + `address already in use` 循环。确需手动时用 `/opt/data/scripts/hindsight_start.sh`。
- **实例密码在 `instances/<name>/instance.json`**（本机 = `hindsight`，不是 postgres）。daemon 经 pg0 自动读取凭据；**自己 psql 探测用错密码会往 pg 日志写 FATAL `password authentication failed`——那是你的探测，不是 daemon 故障**，别被误导。
- **确认某 postgres 进程服务的实例**：`ls -la /proc/<pid>/cwd` → 应指向 `instances/hindsight-embed-hermes/data`；或看 `ps aux | grep postgres.real` 的 `-D` 路径。
- **初始化耗时 40-60s**（加载 embedding/reranker 模型 → 起 postgres → migration），health 检查太早会误报（`curl: exit 7` 不代表起不来，等足再判）。
- 多实例竞争时全清：`ps aux | grep -E "[h]indsight_api.main|[u]v tool uvx hindsight|[p]ostgres.real" | awk '{print $2}' | xargs -r kill -9`（避开 pkill -f 自杀）。
