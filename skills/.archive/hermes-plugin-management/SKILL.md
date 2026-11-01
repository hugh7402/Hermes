---
name: hermes-plugin-management
description: "Enable and verify Hermes bundled plugins."
version: 1.0.0
category: autonomous-ai-agents
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, plugins, plugin-management, activation, verification]
    related_skills: [hermes-agent, hermes-provider-management, hermes-external-memory]
---

# Hermes 插件管理

Hermes 自带 55+ bundled 插件（全部默认关闭、opt-in 启用）。启用、验证生效、排查加载问题是本 skill 的范畴。

## 适用场景

- 用户要装/启用官方插件（disk-cleanup、security-guidance、spotify 等）
- 启用后要确认插件**真正生效**（不只是 config 里 enabled）
- 排查插件不工作（写文件没警告、状态文件没创建）

## 插件类型速览（bundled，`/opt/hermes/plugins/`）

| 插件 | 类型 | 用途 | 生效验证信号 |
|------|------|------|-------------|
| `disk-cleanup` | hooks + slash | 自动清理临时文件 | `$HERMES_HOME/disk-cleanup/tracked.json` + `cleanup.log` |
| `security-guidance` | hooks | 写危险代码时追加安全警告 | write_file 结果里的 `⚠️ Security guidance` |
| `spotify` | backend (7 tools) | Spotify 播放控制 | 工具出现在工具列表 |
| `google_meet` | standalone | Meet 会议转录 | — |
| `observability/langfuse` | hooks | LLM 追踪到 Langfuse | 日志 span |
| `hermes-achievements` | dashboard tab | 成就徽章 | dashboard tab（无需 enable） |
| `image_gen/*` | image backend | 图像生成后端 | 工具可用 |

Memory providers（`plugins/memory/*`）和 context engines 是独立体系，见 `hermes-external-memory`。

## 启用插件

```bash
# 查看全部插件（bundled 显示 not enabled）
cd /opt/data && /opt/hermes/.venv/bin/hermes plugins list

# 启用 —— ⚠️ 一次只能传一个名字，多个会报 unrecognized arguments
/opt/hermes/.venv/bin/hermes plugins enable disk-cleanup
/opt/hermes/.venv/bin/hermes plugins enable security-guidance
```

启用后 config.yaml 的 `plugins.enabled` 追加条目：
```yaml
plugins:
  enabled:
    - disk-cleanup
    - security-guidance
```

## 验证插件真正生效（关键）

`hermes plugins list` 显示 `enabled` **只证明配置写入**，不证明插件代码加载了。验证方法按可靠性排序：

### 1. 行为验证（最可靠）— 触发插件的实际功能

**security-guidance**：用 **write_file 工具**写一个含危险模式的文件（`os.system(` / `eval(` / `pickle.load`），看工具结果是否追加 `⚠️ Security guidance — N patterns matched`。

**disk-cleanup**：write_file 创建 `tmp_*` 或 `test_*` 开头文件后，检查：
- `/opt/data/disk-cleanup/tracked.json`（跟踪列表）
- `/opt/data/disk-cleanup/cleanup.log`（TRACKED 记录）

### 2. 进程级验证（辅助）

gateway 进程（`ps -ef | grep 'gateway run'` 取 hermes 用户的 PID）：
```bash
cat /proc/<PID>/maps | grep -c 'lazy-packages'   # 依赖是否加载进内存
```
对需要大依赖的插件（如 Hindsight 的 torch/triton）有效；纯 hook 插件（disk-cleanup）不留内存映射，**0 处引用不代表没加载**——别据此判死。

### 3. 环境变量验证（插件特有模式）

security-guidance 支持环境变量控制：`SECURITY_GUIDANCE_BLOCK=1`（阻断模式）、`SECURITY_GUIDANCE_DISABLE=1`（kill switch）。未设 = 默认 warn 模式（只警告不阻断）。

## 常见陷阱

- **execute_code 直写文件绕过插件 hook**：在 execute_code 里用 `open()`/Python 写文件**不会**触发 security-guidance 警告，也不会被 disk-cleanup 跟踪。要验证 hook 型插件，必须用 Hermes 的 **write_file 工具**。
- **不要靠 /proc maps 判断 hook 插件**：disk-cleanup/security-guidance 是纯 Python hook，无 .so 映射；maps 里 0 引用是正常的。行为验证才是准的。
- **测试文件记得清理**：写危险代码测试后删除测试文件（`/opt/data/tmp_*.py`），disk-cleanup 会自动跟踪它们。
- **插件启用是 gateway 级**：`plugins.enabled` 由 gateway 启动时 `discover_and_load()` 读取（`gateway/run.py`），重启后生效；当前会话的 write_file 通常也能触发（hook 在 gateway 层注册）。
- **不要手改 /opt/hermes/plugins/ 源码**：只读镜像区（root 所有），写会 Permission denied。用 CLI 或 config.yaml。
- **github 系列是 skills 不是插件**：`hermes plugins` 里没有 github；官方 github skills（github-auth/pr-workflow 等 6 个）在 `/opt/hermes/skills/github/`，直接用无需启用。
