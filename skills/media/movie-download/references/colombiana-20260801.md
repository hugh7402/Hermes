# 《致命黑兰》(Colombiana, 2011) 实战记录 — 2026-08-01

用户需求：**带内嵌中文字幕的高清版**《致命黑兰》（导演奥利维尔·米加顿，编剧吕克·贝松，主演佐伊·索尔达娜），下载到番号视频文件夹。这是 movie-download skill 的首次实战，验证了站点可用性和完整流程。

## 结果

- 选中：`Colombiana.2011.1080p.CATCHPLAY.WEB-DL.H264.AAC-QuickIO`（3.25GB，1080p HDR，**中文字幕**，BT之家 1lou.me 种子）
- btih：`F3975BF8951151F344F44617637860E3A6BC2C2D`
- 已加入 PikPak 离线（Inbox-JAV），等待离线完成后 aria2 拉回
- 首次错误尝试：`Colombiana.2011.US.UNRATED.BluRay.1080p.DTS.x264`（6GB 原版**无中字**）——已删除，因为违反"必须内嵌中字"规则

## 磁链搜索路径（有效）

```
web_search: 致命黑兰 2011 1080p 中字 内嵌 磁力 bt 1lou OR 66s6 OR piaohua
  → 命中 1lou.me 两个帖子：
    - thread-980139: WEB-MKV 3.25GB 中文字幕 1080p HDR（选这个）
    - thread-71342: BD-MKV 6.72GB 英语/中英字幕 1080p（备选）
```

1lou.me 是 Discuz 站，`web_extract` 直接可读全文（无需登录、无 CF）。页面底部 `attachlist` 里有 `.torrent` 附件链接：`attach-download-2952964.htm`。

## 种子下载 + btih 提取

```bash
# 下载种子（curl 走代理）
curl -sL --max-time 30 --proxy http://127.0.0.1:10808 \
  -A "Mozilla/5.0" \
  "https://www.1lou.me/attach-download-2952964.htm" -o /tmp/colombiana.torrent
# 9.4KB，文件头 d8:announce39:http://tracker1.itzmx.com:8080/announce 确认是合法种子

# btih 提取（用 scripts/btih_from_torrent.py）
# 得到 F3975BF8951151F344F44617637860E3A6BC2C2D
```

## 站点可用性实测

| 站点/方法 | 结果 |
|:----|:----|
| 1lou.me web_extract | ✅ 全文可读，种子可下 |
| twlkbt.com web_extract | ✅ 磁链明文在页面里（`magnet:?xt=urn:btih:4DCB8C0F...`） |
| nbwin.com（云盘集）curl | ❌ 海外 IP 拉不到正文（0 字节），浏览器可读但下载链接已失效 |
| yts.mx curl | ❌ SSL 握手失败 (exit 35) |
| 1337x.to / bt4g.org curl | ❌ Cloudflare `Just a moment...` |
| assrt.net curl | ❌ 反爬 812B 错误页 |
| zimuku.org curl | ⚠️ 云锁验证码页 |

## 关键教训

1. **内嵌中字优先是硬规则**——先确认磁链文件名含中字标注再动手，别先把原版加进 PikPak 再删（浪费 PikPak 离线配额和 token 刷新）。
2. **Discuz 论坛（1lou/twlkb）是磁链金矿**——web_extract 直接读，不需过 CF。yts/1337x/bt4g 全部被 CF 拦，别浪费时间。
3. **种子附件 → btih 提取**用 bencode 解析（脚本已存 `scripts/btih_from_torrent.py`），比手动猜 hash 可靠。
4. **字幕源站点（assrt/zimuku）反爬严重**——但本 skill 流程不需要外挂字幕（用户禁止），所以这些站基本用不上。
