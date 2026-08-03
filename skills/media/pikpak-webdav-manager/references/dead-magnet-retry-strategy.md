# 死种/异常磁链重试策略

## 异常判断

| 症状 | 判定 | 
|:----|:----|
| `offline_download()` 成功 → `offline_file_info()` 报 "File or folder is not found" → 60s 后从 offline_list 消失 | **死种**（PikPak 无种源） |
| Inbox 中文件 size=0 且久不变化 | **PikPak 下载失败** |
| javdb 搜索显示 "无磁链" | **番号未上传或无可用种子** |
| **jav_manager.py 报告 "✅ 已完成" 但 Inbox/offline 中查无此文件（2026-07-31 HMN-485 案例）** | **死种——脚本误报成功** |

## 🚨 关键：脚本报成功 ≠ 文件真的在 PikPak（2026-07-31）

**HMN-485 案例**：`jav_manager.py --no-sync HMN-485` 连续两次输出 "✅ 已完成"（Phase 2 全流程走完，还"删了广告文件"），但事后 `file_list(parent_id=inbox_id)` 和全局搜索都查不到该文件，offline_list 也是空的。第三次重新跑脚本仍复现。**根因**：磁链是死种，PikPak 任务创建后从未真正进入下载，脚本的 Phase 2 各步骤对不存在的文件"假成功"。

**教训**：jav_manager 报告完成后，**必须主动验证文件真实存在于 PikPak**：

```python
# 验证步骤：脚本报成功 → 查 file_list 确认 size>0
r = await client.path_to_id('/Inbox-JAV')
files = await client.file_list(parent_id=r[0]['id'])
found = [f for f in files.get('files', []) if 'HMN-485' in f.get('name','').upper() and int(f.get('size',0)) > 0]
# found 为空 → 死种，不要继续等/重跑脚本，直接换磁链
```

若确认死种：**换 javdb 上同一番号的另一个 btih 磁链**（同番号通常 4-10 个磁链），不要反复重跑同一个磁链。换磁链时注意 `-U` 无码破解版仍须排除。

## 重试流程

1. **首次失败** → 立即在 javdb 重新搜索磁链，再次添加
2. **第二次失败** → 等待 30 分钟后再试（PikPak 种子缓存可能刷新）
3. **第三次失败** → 告知用户放弃，建议其他来源

```
jav_manager.py --no-sync 番号
  ├─ ✅ PikPak 有 size → 正常下载
  ├─ ❌ 死种/size=0 → 等 30min → jav_manager.py --no-sync 番号
  │                       ├─ ✅ 正常
  │                       └─ ❌ 再失败 → 等 30min → 第 3 次尝试
  │                                               └─ ❌ 放弃
  └─ ❌ javdb 无磁链 → 尝试 torrentkitty.tv
                          ├─ ✅ 有磁链 → 手动添加
                          └─ ❌ 无 → 告知用户放弃
```

**脚本报成功但文件不存在时**：跳过"等 30min 重跑同一磁链"（同一死种重跑无意义），直接换 btih。

## aria2 CDN 403 处理

CDN URL 在下载中可能返回 `status=403`（CDN 节点限流/旋转）：

```bash
# 症状：aria2 报 errorCode=22, status=403
# 修复步骤：
# 1. 获取新 URL（`api.get_download_url(file_id)` 会分配不同节点）
# 2. rm -f 旧文件（不要 --continue）
# 3. 从头下载
```

新 URL 通常分配不同 CDN 节点（如 `dl-z01a-0048` → `dl-z01a-0043`），可能速度不同。

## 文件级持续限速（2026-07-31 NMSL-011 案例）

个别文件在**连续 4 个不同 CDN 节点**上都只有 20~120 KB/s（换 URL 3 次无效）——这是该文件在 PikPak CDN 的分发问题，不是节点问题。**停止换 URL，删除 PikPak 中的该文件，回 javdb 换不同 btih 的磁链重新离线。** 判定标准：换 2 个节点仍 <500KB/s 且 ETA 以"小时"计 → 换磁链。
