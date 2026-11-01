# PikPak IP 级限流排查实录（2026-08-10）

## 背景

AI短剧批量下载（1248 文件 / 242GB）时，所有文件卡在 0.02~0.09 MB/s，换 URL、降并发（4→3→2）均无效。一度误判为"PikPak CDN 全局限流"，暂停了 3 次等恢复，实际是**服务器出口 IP 被限流**。

## 排查流程

### 1. 误判阶段（浪费的时间）
- 降并发 4→3→2：无效（不是并发问题）
- SLOW 检测 + 换 URL 重排队：机制正常但全是空转（换节点没用，因为所有节点都慢）
- 暂停等 CDN 恢复：测速 cron 每 30 分钟测一次，连续几小时 <1MB/s

### 2. 关键转折 — 对比直连 vs 代理
```bash
# 直连测速（同 URL）
curl -s -o /dev/null -w "%{speed_download}" -r 0-20971520 --max-time 25 "<CDN_URL>"
# → 0.05~0.08 MB/s

# 走代理测速（sing-box 10808 混合端口）
curl -s -o /dev/null -w "%{speed_download}" -x http://127.0.0.1:10808 -r 0-20971520 --max-time 25 "<CDN_URL>"
# → 0.26~0.95 MB/s（不同出口 IP 差异大）
```

### 3. 多节点对比测试
4 个不同 CDN 节点（dl-a10b-1551/1555/1194/0869）直连全部 0.02~0.09MB/s → 排除节点问题。

### 4. 代理出口 IP 对比（proxy_auto_switch.sh --node usXX 逐个切换）
| 出口 IP | 速度 |
|:--------|:----:|
| 134.195.101.193 (us01) | 0.28 MB/s |
| 134.195.101.194 (us02) | 0.27 MB/s |
| 134.195.101.195 (us03) | 0.26 MB/s |
| **103.62.49.138 (us04/us05/AWS日本01)** | **0.86~0.95 MB/s** |
| 134.195.101.180 (us06) | 0.26 MB/s |

→ 出口 IP 不同限流程度不同，103.62.49.138 明显更优。

### 5. aria2 走代理
```bash
aria2c \
    --all-proxy=http://127.0.0.1:10808 \
    --max-connection-per-server=8 --split=8 --min-split-size=8M \
    --dir=<目标> --out=<文件名> "<CDN_URL>"
```
实测：**6~8 MB/s**（8连接分片，远超 curl 单连接 0.95）。

## 后半程关键进展（同一天，务必读完）

### 6. 代理出口 IP 也会二次限流
103.62.49.138 用了约 1 小时后掉回 ~0。该 IP 段（103.62.49.x，AWS日本）所有节点都只有 ~0.95MB/s，且不稳定（断流→恢复→断流），只能下小文件，大文件频繁 SLOW 失败。

### 7. 🏆 最终解法：SG-AWS02（67.159.48.147）= 25~30 MB/s
逐节点测速（用 `proxy_auto_switch.sh --node '<完整节点名>'` + curl 代理测速）发现**出口 IP 段差异可达一个数量级**：
| 节点 | 出口 IP | 速度 |
|:-----|:--------|:----:|
| 🇸🇬AWS新加坡01 | 103.62.49.138 | 0.91 MB/s |
| **🇸🇬AWS新加坡02** | **67.159.48.147** | **7.63 MB/s（curl 30MB），aria2 8连接 25~30MB/s** |

切换命令：`bash /opt/data/proxy-skill/proxy_auto_switch.sh --node '🇸🇬AWS新加坡02'`
效果：242GB 下载在 ~1 小时内完成 170GB（累计均速 36MB/s），从"几小时下几 GB"变成"一小时下 170GB"。

**经验：IP 限流下不要满足于第一个能用的代理节点——逐节点测速，找出口 IP 段差异大的快节点，快节点让整个下载提速一个数量级。**

### 8. 🚨 大文件 SLOW 误杀修复
症状：补下 1.4~4.3GB 大文件全部 `❌ 失败 (SLOW)`，只有小文件成功。
根因：SLOW 检测对大文件中途网络抖动（30s 降速）一视同仁，kill + 删半成品从头再来 → 无限循环。
修复：`aria2_download` 加 `total_size`，**>500MB 直接 `proc.wait()` 跳过 SLOW 检测**（aria2 自带重试）。用户拍板：**大文件取消 SLOW 检测 + 并发 4**。
效果：修复后 1~4GB 大文件全部 27~31MB/s 一次下完，0 失败。

### 9. FAIL 自动重排队
aria2 非 SLOW 错误（超时/断连，reason='FAIL'）也放回队列尾部重试，`task['attempts']` 计数防无限循环（最多 3 次，与 SLOW 共享计数）。用户要求：失败不丢文件。

### 10. 🚨 refresh token 一次性 + 并发刷新冲突
下载脚本 + 测速脚本同时冷启动触发 token 刷新 → 后刷新方报 `refresh token os.XXX has been refresh at`，token 作废。
修复：token 文件有 username/password，`api.login()` 重新登录拿新 token 并落盘。预防：避免多进程同时触发刷新。

## 最终数据

- 直连（服务器 IP 111.193.27.155）：0.08 MB/s
- 代理（103.62.49.138）curl 单连接：0.95 MB/s → 1 小时后被二次限流
- **代理（67.159.48.147 SG-AWS02）aria2 8连接：25~30 MB/s**（最终方案）
- ETA 从 100+ 小时降到 ~1 小时（242GB @ 30MB/s）

## 经验教训

1. **判定 IP 限流**：直连全节点 <0.1MB/s 持续 10+ 分钟 = IP 级限流，不是节点问题
2. **先测代理再切**：`curl -x http://127.0.0.1:10808` 测同一 URL，若明显更快 → 确认走代理
3. **代理节点也要选**：不同出口 IP 限流不同（134.195.101.x 段 0.26 vs 103.62.49.x 段 0.95 vs **67.159.48.x 段 25-30**）——逐节点测速找快节点
4. **代理出口 IP 会被二次限流**：一个出口用 1 小时左右可能掉回 ~0，换节点是常态操作
5. **走代理后 SLOW 阈值要降**：0.5MB/s 会误杀，用户拍板用 **0.2MB/s**
6. **大文件（>500MB）完全取消 SLOW 检测**：aria2 自带重试，中途抖动不杀（用户拍板）
7. **FAIL 也自动重排队**：attempts 计数最多 3 次，失败不丢文件
8. **aria2 用 `--all-proxy` 参数**（不是环境变量），subprocess 里 env 传 LD_LIBRARY_PATH 即可
9. **并发仍按用户现场指定**：本次最终 4 并发 + SG-AWS02，稳定高速
10. **token 刷新避免多进程并发**，冲突后用 login() 重登

## 相关文件

- 下载脚本：`/opt/data/ai_drama_dl.py`（含 `--all-proxy` 开关 + SLOW 检测 + 大文件豁免 + FAIL 重排队）
- 补下脚本：`/opt/data/ai_drama_dl_fix.py`（补 REQUEUE/VERIFY_FAIL 的缺失文件）
- 测速脚本：`/opt/data/scripts/ai_cdn_speed_test.py` + `.sh`
- 代理管理：`bash /opt/data/proxy-skill/proxy_auto_switch.sh --node usXX` / `--node '🇸🇬AWS新加坡02'`
- 结果文件：`/opt/data/ai_drama_dl_result.json`（状态 OK/SKIP/REQUEUE/RETRY/VERIFY_FAIL）
