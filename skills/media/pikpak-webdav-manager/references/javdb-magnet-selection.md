# JAVDB 磁链选择指南

## 选择优先级

当 javdb 搜索返回多个磁链时，按以下优先级选择：

### 1️⃣ 字幕版优先（-C 标记）
文件名包含 `-C` 或描述含「字幕」「中字」 → 优先选
- 优点：自带中文字幕，省去额外搜索
- 示例：`[22sht.me]rbd-664-C`（4.30GB）

### 2️⃣ 干净命名优先
选择文件名简洁、无中文广告植入的磁链：
- ✅ `WANZ-320 (Kurata Mao).mkv`（3.26GB 1080p）— 有女优名，干净
- ✅ `[PPPD-394]巨乳潜入捜査官 佐山愛.mp4`（6.55GB）— 有具体标题
- ❌ `0327-wanz-320-fhdall`（5.81GB）— 可疑的营销类命名
- ❌ `PPPD-394 DVD ISO@★nike★` — 不明来源

### 3️⃣ 大小适中选最大（但要合理）
- 1080p 版本正常范围：3~7GB
- 720p 版本：1~2GB
- 标清：<1.5GB
- 如果声称「5.81GB」但实际只有 937MB → 种子被污染（广告填充）

### 4️⃣ 避免的命名模式
| 模式 | 原因 |
|:----|:-----|
| `fhdall`、`-FHD`、`-all` | 通常是垃圾种子合集 |
| `SIS001@`、`第一會所新片@` | 论坛分享包，可能含广告 |
| 包含 `.torrent` 后缀 | 种子文件本身，非视频 |
| 中文营销名（「最新」「最全」「高清共享」） | 大概率含广告 |

## 兜底策略

1. **第一个磁链污染** → 立即回 javdb 选另一个
2. 优先选有女优全名的磁链（如 `Kurata Mao`、`佐山愛`）
3. 优先选明确标注分辨率的（如 `1080p.mkv`、`FHD`）
4. 字幕版不存在时选最大的干净文件

## 检查 PikPak 结果

磁链加入 PikPak 后，检查返回的是文件还是文件夹：

```python
files = await api.file_list(parent_id=inbox_id)
for f in files.get('files', []):
    if f.get('kind') == 'drive#folder':
        # 检查内部文件大小
        inner = await api.file_list(parent_id=f['id'])
        videos = [fi for fi in inner.get('files', [])
                  if fi['name'].endswith(('.mp4','.mkv','.avi'))]
        for v in videos:
            sz = int(v.get('size', 0))
            print(f'{v["name"]}: {sz/1024**3:.1f}GB')
        # 如果唯一视频明显小于预期 → 种子污染，换磁链
```

## 案例：WANZ-320

第一次选：`0327-wanz-320-fhdall`（声称5.81GB）
- PikPak 创建了文件夹
- 内部含 10+ 广告文件（图片、txt、exe）
- 唯一视频 `wanz320.avi` 仅 937MB

第二次选：`WANZ-320 (Kurata Mao).mkv`（3.26GB 1080p）
- PikPak 正在处理中
- 文件名干净，包含女优名，可靠来源

**教训**：不要被「最大文件」迷惑 — 检查实际视频大小而非磁链声称大小。
