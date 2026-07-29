# 会话记录：2026-07-04 SONE-028 和 REAL-766 下载

## 关键经验

### 1. `-UC` 后缀优于 `-U`
- SONE-028 有 `-U`（23.93GB）和 `-UC`（7.4GB）两个版本
- 用户明确要求选 `-UC`（无码破解+中文字幕）
- `-U` 版已加入 PikPak 后需删除并重新添加 `-UC` 磁链
- 教训：不要仅因文件大小大就选 `-U`，`-UC` 更优（小得多且含中字）

### 2. 大文件 cp/mv 超时修复
- REAL-766（7.0GB）：`mv` 到 Inbox-JAV 时终端超时（10s），文件只写了 5.0GB，ffprobe 报 `moov atom not found`
- 修复：使用 `background=true` + `notify_on_complete=true` 方式 cp/mv，不受前台超时限制
- 最好用后台进程处理 >4GB 的文件复制操作

### 3. 验证流程
- aria2 下载到 `/tmp/dl/` → ffprobe 校验通过 → 后台 cp/mv → 再 ffprobe 验证一次
- 自定义文件名包含中文和空格，要用双引号括起来
