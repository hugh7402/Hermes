# 野兽女孩（Beastie Girls 2016）下载实战 — 假种子识别与换源

日期：2026-08-02。用户要《罪罚野兽》韩国情色片，确认别名 = 《野兽女孩》(Beastie Girls 2016)。

## 片名确认路径

- 用户说"罪罚野兽"，web_search 找不到精确匹配
- 候选：1975 法国《野兽》(The Beast in Heat)、韩国犯罪片《野兽》(2019)、韩剧《罚罪》
- avgood 站内搜"野兽女孩"命中：`비스티걸스.BEASTIE GIRLS, 2016`，确认 = 用户要的片
- **教训**：用户片名可能是俗称/别名，先确认再下载，不要猜。确认后用户说"对 也叫野兽女孩"

## 假种子事故

第一个磁链（avgood c/490279）：`magnet:?xt=urn:btih:168F81B51EB51722C599EC1FC7DA6365152A2546`
- 标注：비스티걸스.BEASTIE GIRLS, 2016.HD.720P.H264-NWBx.mp4（看起来正常）
- PikPak 离线完成 → aria2 拉回 405MB → ffprobe 发现 **duration=284.9s（4分45秒），6838帧**
- 完整电影应为 108 分钟。这就是截断/假种子——PikPak 和 aria2 全程无异常，只有时长能识破
- 抽帧 mjpeg 编码失败（YUV 非标准）也提示文件异常

## 换源成功

第二个磁链（avgood c/250837）：`magnet:?xt=urn:btih:6115DA56C0B1EB807F053D9DD1D4BC641ECAE351`
- 标注：[野兽女孩][韩语][MP4/1.3GB] 720P 103分钟
- PikPak 离线为**单文件**（非文件夹）：`[爱拷电影网ikkao.com]野-兽女-孩.2017.720p.HDRip.x264.aac.mp4` 1.31GB
- 下载后 ffprobe：**duration=6492.8s（108分钟）** ✅
- 取 URL 时直接对文件 id 调 `get_download_url`（单文件无需 file_list 内部查找）

## 字幕验证（无字幕）

- `ffprobe -select_streams s` 无字幕流
- 抽 5 帧（600/1800/2400/3000/4200/5400s）+ RapidOCR：只检测到赌场广告水印（ag96888.com），无任何字幕文字
- subtitlecat 搜索无此片（只有 Beastie Boys 乐队纪录片）
- 结论：韩语无字版。**用户选择：入库但文件名标注"韩语无字幕"，用户自己想办法**

## 关键坑

1. **下载后必须核对时长**：`ffprobe -show_entries format=duration` vs 电影预期时长。这是识别假种子/截断版的唯一可靠手段（文件大小和字幕流都正常时也可能被坑）
2. **小文件"完整电影"高度可疑**：405MB 的"720P 完整版"基本不可能是 108 分钟电影
3. **入库中断要复查**：cp 大文件到 Movie 被中断（orphan recovery）后目标文件只有 1.13GB/1.40GB——移入后必须 `stat -c %s` 对比源文件字节数，不一致就重拷（后台 cp + notify）
4. 无字幕入库要按用户要求标注清楚，不擅自拒绝
