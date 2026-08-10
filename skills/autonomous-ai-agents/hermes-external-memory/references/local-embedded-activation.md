# Hindsight Local Embedded 激活实录（2026-08-09 验证通过）

从"config 配好但从不工作"到 retain/recall 全通的真实调试路径。症状：`~/.hindsight` 从未创建、daemon 进程为 0、`is_available()` False、每次 retain 报 `cannot import name 'HindsightEmbedded'`。

## 根因链（按排查顺序）

1. **本地 daemon 依赖缺失**：Hermes 官方只装 `hindsight-client==0.6.1`（云端 client）。local_embedded 需要额外的 `hindsight-embed` + `sentence-transformers`，官方 pyproject/lazy_deps 都不包含。
2. **Hermes venv 只读**：容器镜像里 `/opt/hermes/.venv` 是 root:root 755，hermes 用户不可写、无 sudo。但容器预设了 `HERMES_LAZY_INSTALL_TARGET=/opt/data/lazy-packages` 和 `HERMES_DISABLE_LAZY_INSTALLS=1` → **依赖必须预先手动装进 lazy-packages**，gateway 通过 `site.addsitedir` 自动加载。
3. **PyPI 的 `hindsight` 是无关包**：`hindsight==0.1.7`（"Python tools for Hindsight Software"）与 Hindsight 记忆项目无关，Py3.13 编译失败（setuptools 2to3）。真正要装的是 `hindsight-embed`（0.9.0，提供 `hindsight_embed` 模块 + `DaemonEmbedManager`）。
4. **LLM key 无效**：插件从 `HINDSIGHT_LLM_API_KEY`（.env）取 key。若该 key 不是有效的 SiliconFlow key，daemon 启动时 LLM 验证 401 → 启动超时。**用当前有效的 SILICONFLOW_API_KEY 覆盖它**。
5. **HF 嵌入模型被墙**：daemon 首次启动要下载 `BAAI/bge-small-en-v1.5` + `cross-encoder/ms-marco-MiniLM-L-6-v2`，直连 HF timed out。解法：先用 `HF_ENDPOINT=https://hf-mirror.com` + `HF_HOME=<缓存目录>` 手动 `SentenceTransformer(...)`/`CrossEncoder(...)` 下载好，daemon 启动复用缓存。注意启动 daemon 时**不要设 ALL_PROXY=socks5**（无 socksio 包会 ImportError；模型已缓存就不需要代理）。
6. **插件旧 API**：插件 `_get_client()` 写死 `from hindsight import HindsightEmbedded`（旧版本地客户端类）。新版 hindsight-embed 无此类。**在 lazy-packages 里建 shim**：`/opt/data/lazy-packages/hindsight/__init__.py` 导出 `HindsightEmbedded`，包装 `DaemonEmbedManager.ensure_running(config, profile)` + `hindsight_client.Hindsight(base_url=daemon_url)`。
7. **api_url 端口不匹配**：插件 local_embedded 默认 `http://localhost:8888`，但 `DaemonEmbedManager` 实际用动态端口（实测 9177）。**config.json 必须加 `api_url: http://127.0.0.1:<实际端口>`**，否则 retain 连错端口、recall 返回 0。
8. **retain_async 影响读后写**：config.json `retain_async: true` 时 sync_turn 后立刻 recall 可能读到 0 条（异步未落库）。验证时改 `retain_async: false`。

## 验证命令

```python
# 1. daemon 启动
import os, sys, site
site.addsitedir('/opt/data/lazy-packages')
sys.path.insert(0, '/opt/hermes')
from hindsight_embed import DaemonEmbedManager
mgr = DaemonEmbedManager()
cfg = {
  'HINDSIGHT_API_LLM_PROVIDER': 'openai',
  'HINDSIGHT_API_LLM_API_KEY': '<有效key>',
  'HINDSIGHT_API_LLM_MODEL': 'deepseek-ai/DeepSeek-V4-Flash',
  'HINDSIGHT_API_LLM_BASE_URL': 'https://api.siliconflow.cn/v1',
  'HINDSIGHT_API_LOG_LEVEL': 'info',
  'HINDSIGHT_EMBED_DAEMON_IDLE_TIMEOUT': '600',
}
print(mgr.ensure_running(cfg, 'hermes'), mgr.get_url('hermes'))

# 2. retain → recall（直连 daemon，绕开插件）
import asyncio
from hindsight_client import Hindsight
async def main():
    c = Hindsight(base_url='http://127.0.0.1:9177')
    r = await c.aretain('hermes', '测试内容', retain_async=False)
    print('retain:', r.success, r.items_count)
    rc = await c.arecall('hermes', '测试', max_tokens=1024)
    print('recall:', len(rc.results), rc.results[0].text[:100] if rc.results else '')
    await c.aclose()
asyncio.run(main())
```

## 注意

- daemon 是懒启动 + idle timeout（默认 300s，config.json `idle_timeout` 可调）自动关闭，下次使用自动拉起——看不到常驻进程是正常的。
- 依赖装进 lazy-packages 后需 **Hermes gateway 重启**（/reset 或重启 gateway）才加载 provider 工具（hindsight_retain/recall/reflect）。
- 若改 config.json 的 api_url/retain_async 等，同样需要重启才生效。

## 重启后 daemon 卡死的根因（2026-08-09 第二次重启发现）

**症状**：daemon 进程在跑（`ps` 可见 hindsight-api）、端口参数对（cmdline 里 `--port 9177`），但 9177 不监听、/health Connection refused，日志反复 `timed out ... huggingface.co/.../modules.json` 直到 300s 超时，然后 `ERROR: Application startup failed. Exiting.`（`memory_engine.py` 的 `init_tasks` 在 `model_init_timeout=300s` 内没完成，`asyncio.TimeoutError` → ExceptionGroup → 启动失败）。

**根因（两段，缺一不可）**：
1. `DaemonEmbedManager` 启动 daemon 时 `env = os.environ.copy()` —— daemon 只继承**调用方进程（gateway/shim 所在进程）的 os.environ**，且 config dict 里**只有 `HINDSIGHT_*` 前缀的 key 会映射进 daemon env**（key_mapping 白名单 + `key.startswith("HINDSIGHT_")` 兜底）。`HF_HUB_OFFLINE` 不是 HINDSIGHT_* 前缀 → 放 config dict 里会被静默丢弃。
2. **`.env` 不会进 gateway 进程环境**！实测 gateway（`/proc/<pid>/environ`）32 个 .env 变量只加载 1 个（HERMES_LAZY_INSTALL_TARGET 来自 s6 容器，不是 .env）。Hermes 读 .env 是**按需**的（`get_secret()` 在插件代码里现读），gateway 启动时的 `load_hermes_dotenv()` 主要处理配置项，不会把全部 .env 导出到 os.environ。所以"往 .env 加 HF 变量 + 重启 gateway"**不保证** daemon 能继承到。

**正确修复（shim 层注入）**：在 shim 的 `HindsightEmbedded.__init__` 里、调 `ensure_running()` **之前**，直接 `os.environ.setdefault(...)` —— 这样 `os.environ.copy()` 就能带上：

```python
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HOME", "/opt/data/.cache/huggingface")
config = {"HINDSIGHT_API_LLM_PROVIDER": ..., ...}  # 只放 HINDSIGHT_* key
self._mgr.ensure_running(config, profile)
```

**验证 daemon 继承到了什么**：`cat /proc/<daemon_pid>/environ | tr '\0' '\n' | grep -E 'HF_|HINDSIGHT'`。改 shim 后**必须重启 gateway**（shim 是 gateway 进程内 import 的，改文件不影响已加载代码）。

**其他坑**：
- `hindsight-api` 的 `--idle-timeout 300` 是 daemon 空闲超时；启动失败的 300s 是 `model_init_timeout`（`HINDSIGHT_API_MODEL_INIT_TIMEOUT` 可调），别混淆。
- daemon 每次启动失败会留下 `Application startup failed. Exiting.` 后自杀，`ps` 看不到残留进程，只能从 profile log 判断。`~/.hindsight` 相对路径随 HOME 变（见下节），日志文件看 `fd 1/2` 指向（`/proc/<pid>/fd` 里的 `hermes.log`）。

## pg0 / .hindsight 数据目录分裂（2026-08-09）

**症状**：`/opt/data/.pg0` 和 `/opt/data/home/.pg0` 两套实例（各 40-170MB），`/opt/data/.hindsight` 和 `/opt/data/home/.hindsight` 两套 profile，daemon 时而用这套时而用那套。

**根因**：`ProfileManager.resolve_profile_paths()` 用 `Path.home() / ".hindsight"` 决定 profile 位置；pg0 实例目录也随 HOME 变。gateway 的 s6 run 脚本设 `HOME=/opt/data`（容器环境），但某些手动/旧进程用 `/opt/data/home` → 两套数据各写各的。

**判定标准**：`cat /proc/<gateway_pid>/environ | tr '\0' '\n' | grep HOME` —— gateway 用哪个 HOME，哪套就是权威。本机（Hermes 容器）权威 HOME 恒为 `/opt/data`。

**⚠️ 分裂会反复发生（本机实际踩了两次）**：第一次是历史遗留；第二次是我自己写验证脚本 `verify_*.py` 时没设 HOME，直接继承 shell 的 `HOME=/opt/data/home`，`DaemonEmbedManager` 一跑就又在 `/opt/data/home` 重建了一整套 `.pg0` + `.hindsight`。**因此所有手动启动/验证脚本必须第一行就 `os.environ['HOME'] = '/opt/data'`，严禁依赖环境继承。**

**防分裂铁律（本机）**：
- Hindsight 数据只允许存在于：`/opt/data/.hindsight`（profile）、`/opt/data/.pg0`（数据库）、`/opt/data/.cache/huggingface`（模型缓存）。
- 出现 `/opt/data/home/.pg0` 或 `/opt/data/home/.hindsight` = 分裂事故，立即清理（先杀孤儿 postgres 再删）。
- 手动写任何 daemon 相关脚本（验证/调试），脚本里显式 `os.environ['HOME'] = '/opt/data'`。
- 自查命令：`ls -d /opt/data/home/.pg0 /opt/data/home/.hindsight 2>/dev/null` 应无输出；`cat /proc/<daemon_pid>/environ | tr '\0' '\n' | grep -E '^HOME='` 应为 `/opt/data`。

**清理**：删非权威那套（`.pg0` 实例 + `.hindsight` profile），但**模型缓存单独处理**——HF_HOME 指向的 huggingface 缓存（含 bge-small + cross-encoder，约 300MB）先 `copytree(symlinks=True)` 迁到标准路径（如 `/opt/data/.cache/huggingface`），再更新 .env 的 `HF_HOME`，最后删旧缓存。删库会丢已 retain 的记忆（测试数据无碍，正式记忆重启后重新积累）。

## 标准库损坏 / PG 起不来（2026-08-09 第三次重启发现）

**症状**：daemon 启动失败，日志尾部（注意它混在旧日志里，按进程 PID 搜索）报：
`RuntimeError: Failed to start embedded PostgreSQL after 5 attempts ... pg_ctl: could not start server`。标准实例目录 `/opt/data/.pg0/instances/hindsight-embed-hermes/data` 缺 PG 必需目录（`pg_notify`、`pg_commit_ts`、`pg_dynshmem`、`pg_replslot`、`pg_serial`、`pg_snapshots`、`pg_stat`、`pg_stat_tmp`、`pg_tblspc`、`pg_twophase` 等十几个）——`pg_ctl` 因缺 `pg_notify` 直接 FATAL，5 次重试全失败。

**根因链**：
1. **测试/验证脚本带错了 HOME**：`verify_*.py` 里如果 `os.environ['HOME'] = '/opt/data/home'`（当前 shell 环境常见），会拉起一套 HOME=/opt/data/home 的 daemon **和它自带的嵌入式 postgres**。
2. **杀 daemon 不杀 postgres**：嵌入式 postgres 是独立进程（reparent 到 PID 1），daemon 被 kill 后 postgres 变孤儿继续跑、占端口。`ps -ef | grep postgres` 能查到 `/opt/data/home/.pg0/.../postgres`。
3. **孤儿 postgres 运行期间删它的数据目录**（`shutil.rmtree('/opt/data/home/.pg0')` 清理分裂数据时），或删标准库目录时 postgres 还在写——留下不完整的 PG 数据目录，下次启动起不来。

**修复（实测 73s 全通）**：
```bash
# 1. 清掉所有孤儿（postgres 是孤儿进程，必须单独杀；杀 daemon 不够）
pkill -9 -f 'postgres' ; pkill -9 -f 'hindsight-api' ; sleep 2
ps -ef | grep -E 'postgres|pg0'   # 确认 0 残留
# 2. 删损坏实例 + 旧锁/日志，让 daemon 全新 initdb
rm -rf /opt/data/.pg0/instances/hindsight-embed-hermes
rm -f /opt/data/.hindsight/profiles/hermes.lock /opt/data/.hindsight/profiles/hermes.log
# 3. 下次 daemon 启动自动重建（模型加载 + initdb + LLM 验证 ≈ 73s）
```
重建后 retain/recall 验证通过；之前积累的记忆丢失（测试数据无碍）。

**教训**：验证脚本里**显式设 `HOME=/opt/data`**（与 gateway 一致），别依赖环境继承；测试完除了杀 daemon 还要检查并杀它拉起的 postgres 孤儿。判断 daemon 实际用哪个库：`cat /proc/<daemon_pid>/fd/1` 看日志指向，或 stderr 里 `Database: ...` 行。

## hook 型插件（security-guidance/disk-cleanup）验证方法

- **execute_code 里用 Python `open()` 直写文件会绕过插件 hook**（post_tool_call 不触发）。必须用 Hermes 的 `write_file` 工具写内容才触发 security-guidance 警告。
- security-guidance 验证：write_file 写含 `eval(`/`os.system`/`pickle.load` 的文件 → 工具结果尾部出现 `⚠️ Security guidance`。默认 warn 模式（文件照写），`SECURITY_GUIDANCE_BLOCK=1` 才阻断。
- disk-cleanup 验证：写 `tmp_*`/`test_*` 文件后看 `$HERMES_HOME/disk-cleanup/tracked.json` + `cleanup.log` 是否有 TRACKED 记录。
- 插件加载状态：`hermes plugins list | grep <name>` 显示 enabled 即配置生效；但**当前已建立的会话可能不加载新启用的 hook 插件**（hook 注册在会话/gateway 生命周期绑定），验证以实际行为（警告/tracked.json）为准，别只看配置。
