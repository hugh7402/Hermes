# 限速换版、字幕质量、PikPakApi 改名——实战踩坑

## 1. 「换小版本」不必真小，换的是种源

同一个番号不同磁链，体积差 14% 也可能速度差 300 倍。

MIDA-843 实测（同一条代理线路 127.0.0.1:10808，同一时段）：

| 版本 | 体积 | 实测速度 | ETA |
|---|---|---|---|
| `MIDA-843-LTX` | 7.74GB | 0.2–0.4 MB/s | 38分→51分，越跑越慢 |
| `MIDA-843` | 6.68GB | **97 MB/s** | 1 分 20 秒 |

结论：**卡在几百 KB/s 就换磁链，不要拿体积差小当理由排除它**。差别在 swarm（做种端），不在文件大小。换之前先 `proxy.sh status` 看出口 IP 是否已换过——如果切节点后 IP 没变（本来就是那个节点），就不是节点配额问题，直接换版本。

## 2. prep_dl.py 固定选最大版，要小版本必须手动提交

`prep_dl.py` 的选版逻辑是 `pick = biggest`（除非有 `-C` 且 ≥90%），没有参数能改选小版本。要换版本时：

1. 从 javdb 详情页取目标版本的 btih
2. 手动 `c.offline_download(magnet, parent_id=inbox)` 提交
3. 轮询 `c.file_list(parent_id=inbox)` 找文件夹
4. 移出主视频 → 改名 → 删垃圾文件和空文件夹

参考实现：`/opt/data/.tmp_tests/mida843_alt.py`、`mida843_fix.py`。

## 3. PikPakApi 方法名（易错）

`PikPakApi` **没有** `rename_drive_files`，调它会 `AttributeError`。正确方法：

```python
await c.file_rename(id=file_id, new_file_name='新名字.mp4')
await c.file_batch_move(ids=[file_id], to_parent_id=inbox_id)
await c.delete_to_trash([id1, id2])
await c.delete_forever([id])          # 彻底删，不走回收站
await c.offline_download(magnet, parent_id=inbox_id)
await c.path_to_id('/Inbox-JAV')      # 返回 list，取 [0]['id']
```

改名要在**移出文件夹之后**做——在文件夹内改名会导致后续按番号前缀匹配失效。

## 4. 重复提交离线 = 云端双份

同一个磁链提交两次离线，云端会同时出现 `DSOD-095.mp4` 和 `DSOD-095(1).mp4`，字节数完全相同。

处理：`rclone moveto` 把主份改成目标名，再 `rclone deletefile` 删掉 `(1)` 副本。**校验字节数再删，别只按文件名判断**。

## 5. 字幕质量：汉字数达标不等于能用

`fetch_sub_srt.sh` 只报汉字数，不报质量。必须自己看条数和内容。

MIDA-843 实例：150 分钟片子只有 **209 条 / 2,544 汉字**，平均 43 秒一条。抽头部几行看到：

```
桃田要来是因为我告诉他他被从训练架上除名了。
大额养老金用得太武力了。变得更柔软，更坚强。
压缩设施保留供私人使用。
```

原文是田径教练讲动作要领，机翻完全读不通，且大部分对白缺失。**这种字幕删掉比留着好**——留着是干扰。

判定标准（经验值）：

| 片长 | 条数 | 判定 |
|---|---|---|
| 120–180 分 | < 400 条 | 大概率残缺，必看内容 |
| 120–180 分 | 600–1500 条 | 正常 |
| 任意 | 汉字 < 3,000 且片长 > 120 分 | 必看内容再决定 |

抽样命令：

```bash
head -40 "$SRT"                     # 看前几行译得通不通
python3 -c "import re,pathlib;t=pathlib.Path('$SRT').read_text(errors='ignore');print(len(re.findall(r'^\d+\s*$',t,re.M)),'条')"
```

## 6. 字幕时间轴核对

拿字幕最后一条时间戳和视频时长比：

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$F"
python3 -c "import re,pathlib;ts=re.findall(r'(\d{2}:\d{2}:\d{2})[,.]\d{3}',pathlib.Path('$SRT').read_text(errors='ignore'));print(ts[-1])"
```

差几十秒到 2 分钟正常（字幕自然在片尾前结束）。

字幕从 `-UB` 等其他版本页面抓到的也可能对得上（SNOS-439 字幕来自 `-UB` 页面，结尾 02:24:42 vs 片长 02:26:37，差 1 分 55 秒，正常）。

## 7. `-C` 版硬字幕必须抽帧验语言

DLDSS-547-C 抽 20 帧才敢定论：第一轮 8 帧里有 1 帧是日文（「口ではうまいこと言っても、体は正直だ」），怕是全日文硬字幕；第二轮抽 12 帧确认 3 帧简体中文（「你们当心点 这是上好的奶啊」「流川风 是的」「……不行」），中文占比压倒性。

**单帧或少量帧出现日文不要立刻判死**——多抽两轮，20 帧量级再看比例。真全日文才走 `fetch_sub_srt.sh` 补挂；中文为主就别叠外挂，会重复显示。
