# 重启 gateway 并验证它真的重启了

适用：s6 监管的 Docker 部署（`/run/service/` 下能看到 `gateway-default`、`main-hermes`、`dashboard`）。

## 1. 不能在 gateway 进程内重启 gateway

从对话里调 `terminal` 执行重启会被 Hermes 主动拦住：

> Blocked: command or referenced script cannot restart, stop, or uninstall the gateway from inside the gateway process. The gateway would kill this command before it could complete (SIGTERM propagates to child processes).

连 `bash -n 重启脚本.sh` 这种只是"引用了那个脚本"的命令也会被拦。**让用户在一个独立终端里执行**，别把"排个延迟后台任务"当成解法写进流程——那条路会在中途被 SIGTERM 打断。

## 2. 控制命令的绝对路径

```bash
/command/s6-svc -r /run/service/gateway-default
```

`s6-svc` **不在默认 PATH 里**，裸写命令名会得到 exit 127（`s6-svc: command not found`），而脚本如果只把输出重定向进日志、不检查退出码，就会**静默失败**——用户以为重启了，其实没有。包装脚本里写死 `/command/s6-svc` 并检查 `-x`，找不到再回退 `hermes gateway restart`。

## 3. 🚨 验证重启：别盯错进程

这是最容易得出错误结论的地方。s6 部署下有**两个**带 gateway 字样的进程：

| 进程 | 是什么 | 重启后会变吗 |
|---|---|---|
| `main-wrapper.sh gateway run`（PPID 1） | s6 的外层 init/wrapper | **不会**，设计上常驻 |
| `s6-supervise gateway-default` 的子进程 | 真正的 gateway worker | **会**，PID 和启动时间都换 |

看 wrapper 的 PID 和 `etime` 得出"没重启成功"是错的。正确的三种验法：

```bash
hermes gateway status                     # 直报 worker PID，最直接
ps -eo pid,ppid,lstart,cmd | grep gateway # 看 s6-supervise gateway-default 的子进程
```

如果用户说"已经重启了"而你看 wrapper 没变，**先怀疑自己查错了进程**，再怀疑用户。

## 4. 验证配置/hook 是否真的加载

重启后不要只看进程活着，要看**加载日志**：

```bash
grep -iE "hook|Loaded" <gateway日志目录>/current | tail
grep -c "Loaded hook '<hook名>'" <gateway日志目录>/current
```

预期能搜到形如 `[hooks] Loaded hook 'hindsight-keepalive' for events: ['agent:end']` 的行。
**hook 只在 gateway 启动时扫描一次**——装了 hook 但没重启，日志里就一行都不会有，这是判断"hook 到底生效没有"的唯一硬证据。

订阅 `agent:end` 的 hook 在当轮对话结束时才写日志；重启后立刻查自己的日志文件为空是正常的，不代表没生效。

## 5. 配置改动同样需要重启

`hermes config set` 写进 `config.yaml` 后，运行中的 gateway 不会重读。改 `fallback_providers`、hook、模型这类配置，必须重启才生效；改完先用 CLI（`hermes chat -q ... --model X --provider Y`）验证配置本身正确，再安排重启。
