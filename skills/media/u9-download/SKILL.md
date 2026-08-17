---
name: u9-download
description: 网页视频列表→过滤(时间/大小)→标题去重→PikPak离线指定文件夹。u9a9.com已验证
tags: [U9, u9a9, 网页抓取, PikPak离线, 去重, 视频下载]
trigger: 用户说"U9下载"、"下载网页视频"、"u9a9.com"、"给网址下载所有视频"、"烈@Retsu_dao" 或要求"从网页抓视频离线到PikPak"时使用
---

# U9 下载（网页视频 → PikPak 离线）

给定网页（如 u9a9.com 搜索页）→ 抓取全部视频 → 时间/大小过滤 → 标题去重 → PikPak 离线到指定文件夹。

## 交互协议（2026-08-14 用户定义）——启动时必须先列模板

用户说 **"启动U9下载skill"** → 必须先列出以下 4 项模板，等用户填写后再执行：

```
1、需下载的具体网址：
2、具体时间要求：（如：从2025年11月到现在的所有视频）
3、具体视频大小要求：（如：1GB以上的才下载）
4、将视频文件离线存入PikPak的位置：（如：/网络视频/烈@Retsu_dao）
```

> ⚠️ 4 项缺一不可。用户没填的项按默认处理：时间=不限、大小=不限、位置=必须确认。
> 位置必须是 PikPak 完整路径（如 `/网络视频/xxx`），解析时注意 @ 坑。

## 用户需求五要素（每次都要确认）

1. **网址**：视频列表页 URL
2. **时间范围**：如"2025年11月到现在"
3. **大小下限**：如"≥1GB"
4. **去重规则**：按标题关键词去重，同视频保留体积最大（清晰度高）
5. **目标文件夹**：PikPak 指定路径（可能是二级目录！）

## u9a9.com 解析（已验证 2026-08-12）

**纯静态 HTML，不需要 crawl4ai**。curl + 正则即可：

```bash
curl -s --proxy http://127.0.0.1:10808 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
  "https://u9a9.com/?type=2&search=Retsu_dao" -o /tmp/u9_page.html
```

**每个视频条目 = `<tr class="default">`**，字段：
- 视频页：`href="/view/2/{btih}"` → btih 就是磁链 hash
- 磁链直接可用：`href="magnet:?xt=urn:btih:{hash}&tr=..."`（记得 `&amp;` → `&`）
- 大小列：`<td class="text-center">1.22 GB</td>`
- 时间列：`<td class="text-center">2026-08-06 05:27:21</td>`
- 标题：`title="..."` 内含清晰度/时长/格式（如 `[1.1G/54:26/MP4]`）
- 无分页（搜索结果显示单页全部），但**检查底部 `<ul class="pagination">` 确认**

## 过滤与去重

```python
# 过滤：date >= cutoff 且 size_gb >= 1.0
# 去重：按标题关键词（同系列同集数/同核心描述），保留 size 最大
```

⚠️ **去重匹配坑**：PikPak 里解包后的文件名可能带 `2048.vip-` 前缀、`1 烈...` 前缀、`【U5A5.COM】_全網最新國產資源站_xxx` 广告文件夹。对比"已存在"时：
- 去掉 `2048.vip-`、编号前缀、扩展名后再匹配
- 用标题核心前 12-18 字符包含匹配（`t[:12] in en or en[:12] in t`），防止全前缀误判
- 第一版用"前 14 字符做组键"会**把同一创作者不同视频全误判成重复**——必须提取内容核心而非开头

## PikPak 离线（⚠️ 致命坑区）

### ⚠️ 坑1：path_to_id 对含 @ 的二级路径解析失败！

```python
await api.path_to_id('/网络视频/烈@Retsu_dao')
# ❌ 返回的是 /网络视频 的 id（父目录）！不是 烈@Retsu_dao！
```
含 `@` 的二级路径 path_to_id 会静默回退到父目录 → 磁链全加到父目录。

**正确做法**：file_list 逐级查找，或先 path_to_id('/网络视频') 再 file_list 子文件夹里按 name 精确匹配 `烈@Retsu_dao` 拿 id。添加后**验证**：file_list(parent_id=目标id) 确认文件真在里面。

### ⚠️ 坑2（致命）：离线后不要过早清理文件夹！

PikPak 磁链解包后，文件夹里**广告文件先就绪，大视频还在下载**。如果此时遍历文件夹判断"无大视频 → 删除整个文件夹"，会把**还没下载完的视频连带删除**，且离线任务从此失效（`Task does not exist`），回收站里也找不到（删文件夹连带子文件是彻底删）。

**正确时序**：
1. 添加磁链 → **等 PHASE_TYPE_COMPLETE**（轮询离线任务或文件夹内容）
2. 文件夹里出现 >100MB 的视频文件后才清理
3. 清理：删广告 → batchMove 视频到目标根 → **验证目标确实出现该视频** → 才删空文件夹

### ⚠️ 坑2b（本会话丢 10+ 视频的真凶）：batchMove 是异步的，HTTP 200 ≠ 移动完成！

```python
resp = await client.post(url, json={"ids": [vid_id], "to": {"parent_id": TARGET}}, headers=hdrs)
# resp.status_code == 200 只说明请求被接受，移动可能还没生效！
# 立刻 delete_to_trash([folder_id]) → 视频还在文件夹里 → 被连带彻底删除
```

日志会显示"✅ 移出成功"但目标目录根本没有该文件——**假成功**。必须：

```python
await asyncio.sleep(2)  # 等移动生效
r3 = await api.file_list(parent_id=TARGET, size=100)
tgt_names = [f['name'] for f in r3.get('files', [])]
verified = any(vname in n or n in vname for n in tgt_names)
if verified:
    # 确认目标里有才删文件夹
    await api.delete_to_trash([folder_id])
else:
    print("⚠️ 移动未验证，保留文件夹不删")
```

### 坑3：删除 = delete_to_trash（可恢复），但连带删除不可恢复

- `delete_to_trash(ids)` 移入回收站，可用 `untrash(ids)` 恢复
- 回收站列表：`GET /drive/v1/files?trashed=true&page_size=200`（需刷新 token）
- **删文件夹时如果视频还在里面 → 视频被彻底删，回收站无**（本次丢失 10+ 视频的根因）

### 坑4：假种子识别——磁链本身就是广告

- 任务名带 `【U5A5.COM】_全網最新國產資源站_xxx` / `2849.【U6A6.SU】...` = **广告假种子**，解包后全是 U5A5/U6A6 广告图（jpg/png/7z），**无视频**
- 网页列表里某些条目（尤其较新的）磁链被替换成广告种子，`offline_download` 会成功但任务名是广告站
- 识别后直接取消，不要等下载；同一磁链**反复添加会被 PikPak 静默拒绝**（任务列表 0 命中、无新文件夹），别浪费重试

### 坑5：死种特征

- `offline_list()` 显示 progress 卡在 5-8、`status=None`、`task_id=None` → 种子无源
- `offline_task_retry(file_id)` 报 `Task does not exist`（文件夹被删后任务已失效，无法重试）
- 处理：按 10 分钟规则取消；单 btih 无替代磁链时如实汇报"死种/假种子"，不要反复重试

## 用户规则：10 分钟下载超时机制

用户要求（2026-08-12）：
- 视频离线到 PikPak 后，**设 10 分钟下载时限**
- 10 分钟没下载完：
  - **有该视频其他重复磁链**（同标题不同 btih）→ 取消旧任务，换磁链重下
  - **无其他磁链** → 取消并删除任务

实现：监控脚本 `/opt/data/scripts/u9_monitor.py`（每 600s 扫描）：
- 记录每个文件夹开始时间到 `/tmp/u9_monitor_state.json`
- 完成 → 提取视频删广告；超时 → 查 `/tmp/u9_all_videos.json` 同标题候选，有则换 btih 重加，无则删除

## 参考脚本/文件

- `/opt/data/scripts/u9_monitor.py` — 10 分钟超时监控 + 完成清理
- `/tmp/u9_final_list.json` — 过滤去重后清单
- `/tmp/u9_all_videos.json` — 网页全部原始视频（含所有 btih，供换磁链）
- 代理：javdb/U9 均需走代理（`proxy.sh`），us03=134.195.101.195 当前可用
- `references/pikpak-move-verify.md` — batchMove 验证清理工作流 + 假种子/死种识别（2026-08-14 丢视频教训）

## 验证清单（下载完成后核对数量）

**数量对不上时先怀疑匹配误报，再怀疑真丢失**：
1. 目标目录 file_list 全名打印，与清单**人工核对**（自动匹配对带 `2048.vip-`/`1 ` 前缀的文件名极易误报）
2. 回收站 `files?trashed=true` 查大文件（>100MB）——有则可 `untrash` 恢复
3. 真丢失 → 从 `/tmp/u9_all_videos.json` 重新添加磁链
4. 重新添加后**必须等下载完成再清理，move 后验证目标出现才删文件夹**（坑2b）
5. 最终如实汇报：成功 N/34 + 死种/假种子清单（坑4/坑5），不要报"全部成功"

## 已验证结论

- 网页抓取：✅ curl+正则（无需 crawl4ai）
- 磁链/大小/时间提取：✅
- 去重：✅ 标题关键词，保留最大
- PikPak 离线到指定文件夹：⚠️ 路径解析有 @ 坑，必须验证落点
- 清理：⚠️ 必须等下载完成 + batchMove 验证后才删文件夹，否则删视频
- 数量核对：⚠️ 自动匹配会误报，缺失清单必须人工核对文件名
- 磁链质量：⚠️ 部分条目是广告假种子（U5A5/U6A6）或死种，如实汇报
