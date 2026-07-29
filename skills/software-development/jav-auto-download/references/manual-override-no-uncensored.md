# 手动覆盖：跳过无码破解版（-UC/-U）

## 场景

用户说「不要下载无码破解版本」或明确要求跳过 `-UC`/`-U` 磁链时，`jav_manager.py` 的自动选择规则默认优先选最大文件（通常是 -U 无码版），需要手动干预。

## 完整工作流

### Step 1: 检查脚本自动选了什么

```bash
/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --no-sync DSOD-008
```

查看输出中的 "选中:" 行——如果带 `-U` 或 `-UC` 标记，说明脚本选了无码版。

### Step 2: 从 PikPak 删除错选的文件

```python
# 查找 Inbox-JAV 中的文件并删除
inbox = await client.file_list(parent_id='')
inbox_id = next(f['id'] for f in inbox.get('files',[])
                if f.get('kind') == 'drive#folder' and 'inbox' in f.get('name','').lower())
inbox_files = await client.file_list(parent_id=inbox_id)
for f in inbox_files.get('files', []):
    if 'DSOD-008' in f.get('name','').upper():
        await client.delete_to_trash([f['id']])
```

### Step 3: 上 javdb 找有码版磁链

```bash
curl -s -x socks5h://127.0.0.1:10808 -b /tmp/jdb_cookies.txt \
  "https://javdb.com/v/{video_id}" | grep -oP 'magnet:\?[^"]+|class="name">[^<]+'
```

分析磁链列表，去掉 `-UC`、`-U`、文件名含「无码」的。选出：
- 有 `-C` 标记的优先（内嵌字幕）
- 无标记的裸 `番号.mp4` 版其次（需从 subtitlecat 补充字幕）
- 大小 ≥ 2GB

### Step 4: 手动添加磁链到 PikPak

```python
magnet = 'magnet:?xt=urn:btih:5604...&dn=DSOD-008'
result = await client.offline_download(magnet)
task = result.get('task', {})
task_id = task.get('id', '')
file_id = task.get('file_id', '')
```

### Step 5: 等待完成 + 清理广告

```python
# 等任务完成
import asyncio
for i in range(20):
    try:
        info = await client.offline_file_info(task_id)
        if info.get('phase') == 'PHASE_TYPE_COMPLETE':
            break
    except:
        pass
    await asyncio.sleep(3)

# 如果是文件夹，列出文件
fid = task.get('file_id', '') or info.get('file_id', '')
files = await client.file_list(parent_id=fid)
for sf in files.get('files', []):
    print(f'{sf["name"]} ({int(sf.get("size",0))//1048576}MB) phase={sf.get("phase")}')

# 分类：视频 vs 广告
video = [sf for sf in files.get('files',[])
         if sf.get('kind')=='drive#file' and sf['name'].endswith(('.mp4','.mkv'))
         and '番号' in sf['name'].upper()]
ads = [sf for sf in files.get('files',[])
       if sf['id'] not in [v['id'] for v in video]]

# 删广告
if ads:
    await client.delete_to_trash([a['id'] for a in ads])

# 移出视频到根目录（不用 Inbox-JAV，后续移入）
await client.file_batch_move([video[0]['id']], '')

# 重命名（可选）
try:
    await client.file_rename(video[0]['id'], '番号.mp4')
except:
    pass  # 名字相同会报 Name not changed，忽略

# 删空文件夹
await client.delete_to_trash([fid])
```

### Step 6: 移入 Inbox-JAV

```python
root = await client.file_list(parent_id='')
inbox_id = next(f['id'] for f in root.get('files',[])
                if f.get('kind')=='drive#folder' and 'inbox' in f.get('name','').lower())
# 找到刚移出的文件
for f in root.get('files', []):
    if '番号' in f.get('name','').upper() and f.get('kind') == 'drive#file':
        await client.file_batch_move([f['id']], inbox_id)
        break
```

### Step 7: 获取 CDN 直链 + aria2 下载

```python
inbox_files = await client.file_list(parent_id=inbox_id)
for f in inbox_files.get('files', []):
    if '番号' in f.get('name','').upper():
        dl = await client.get_download_url(f['id'])
        url = dl.get('web_content_link', '') or dl.get('url', '')
        # url → aria2 --continue=true --out=番号.mp4
        json.dump({'番号.mp4': url}, open('/tmp/番号_url.json','w'))
```

## 磁链不易被 PikPak 处理时的替代方案

部分磁链（尤其是裸 btih 不带 tracker 的）可能在 PikPak 上处理失败。此时可以：
1. 试试 kks11.cc 等第三方来源的磁链（通常也是有效文件，多了广告视频，但清理后一样）
2. 换一个 btih hash（同番号可能有多个 tracker 的版本）
3. 如果所有磁链都不行，告知用户
