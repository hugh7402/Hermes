# 内嵌字幕检测与跳过逻辑

## 规则

如果选中磁链文件名含 `-C` / `-UC` / `中字` / `内嵌` / `SUB` / `字幕` 等标记，说明视频已内嵌字幕轨道，**跳过** subtitlecat 下载独立 .srt 文件。

## 实现位置

`jav_manager.py` 的 `download_code()` 函数中 Phase 2.5 部分：

```python
if not sel['has_subtitle']:
    # 裸磁链版 → 搜 subtitlecat
    subs = search_subtitle(code)
    ...
else:
    print('  ℹ️ 影片含内嵌字幕')
```

## `select_best()` 中 has_subtitle 的判断

基于磁链文件名中的关键词：

```python
has_subtitle = any(s in magnet_name.upper() for s in ['-C', '-UC', '_C', '_UC', '中字', '内嵌', 'SUB', '字幕'])
```

## 优先级（2026-07-08 确认）

1. **首选内嵌中文字幕版**（-C / -UC 后缀）
2. **次选高清**（同类中选最大文件）
3. **兜底** subtitlecat 下载独立 .srt（仅裸磁链版）

## 文件名保留

- 内嵌字幕版最终文件保留 `-C` 后缀：`SNOS-341-C.mp4`
- 自定义重命名时去掉 `-C` 后缀，使用用户指定的完整文件名
