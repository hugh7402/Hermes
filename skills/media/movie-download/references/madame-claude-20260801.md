# 《应召女王》(Madame Claude, 2021) 实战记录 — 2026-08-01

用户需求：下载《应召女王》（Madame Claude，2021 法国 Netflix 电影，导演西尔薇·维尔海迪）。movie-download skill 第二次实战，验证流程可复用。

## 结果

- 选中：`克劳德夫人[中文字幕].Madame.Claude.2021.1080p.NF.WEB-DL.x264.DDP5.1-10006@BBQDDQ.COM`（2.72GB，1080p，**中文字幕**，BT之家 1lou.me 种子）
- btih：`BA667B191E624DB68183159089FE33F795197212`
- 已加入 PikPak 离线（Inbox-JAV），等待离线完成后 aria2 拉回

## 磁链搜索路径（有效）

```
web_search: 应召女王 2021 1080p 中字 磁力 bt
  → 命中 1lou.me 多个帖子（克劳德夫人/克劳蒂夫人 译名），筛选：
    - thread-242985: 克劳德夫人[中文字幕].1080p 2.72GB（选这个）
    - thread-295632: 简繁英字幕 1080p（备选）
    - thread-814629: 2160p 13.94GB（太大，除非用户要 4K）
```

注意：该片中文译名有多个——**应召女王 / 克劳德夫人 / 克劳蒂夫人**（大陆/台/港译名不同），搜索时要同时试。

## 种子下载 + btih 提取

```bash
# 页面 HTML 里 grep attach-download 找附件 id（本片为 412612）
curl -sL --max-time 30 --proxy http://127.0.0.1:10808 \
  -A "Mozilla/5.0" \
  "https://1lou.me/attach-download-412612.htm" -o /tmp/madame_claude.torrent
# 11.8KB 合法种子 → scripts/btih_from_torrent.py 提取 btih
```

## 与首次实战（致命黑兰）的差异点

1. **译名多**：一部片可能有 3+ 中文译名，web_search 要轮换关键词
2. **BT之家有两个域名**：`www.1lou.me` 和 `1lou.me` 都能访问，seed 附件页通用
3. **版本筛选维度**：除了"中字"还要看清晰度（1080p vs 2160p）和体积——用户默认要高清但没说 4K，1080p 中字是安全默认

## 待办（会话结束时未完成）

- PikPak 离线完成后：取 CDN URL（注意可能是文件夹，需 file_list 找子文件）→ aria2 拉回 → ffprobe 校验 → 重命名入库 Inbox-JAV
