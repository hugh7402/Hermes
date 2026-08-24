---
name: chinese-novel-txt-download
description: 用户要下载小说TXT/精校版时用。资源站地图+知轩藏书/116盘流程+止损给地址。
tags: [novel, txt, download, 小说, 精校, 网盘]
trigger: 用户要求下载小说/TXT/精校版/全集/完本
---

# 中文小说 TXT 下载

用户要小说txt时用本技能。精校版优先，其次在线全本。

## 资源站优先级（2026-08 实测）

1. **知轩藏书**（精校专业站）— 书在第三方网盘（116盘），精校质量最好
2. **69书吧**（69shuba.com）— 在线全本可爬，起点原文字，非精校
3. **爱下电子书**（ixdzs8.com）— 有直链zip，但**部分书缺章节**（用户实测黜龙缺章），只能当备选
4. 精校吧（jingjiaoba.com）— 站内搜索常搜不到新书，别浪费时间

## 各站操作

### 爱下电子书 ixdzs8
书页 `/read/{bookid}` 的 HTML 里有直链：
```
curl -sL 书页 | grep -oE 'href="https://down[0-9]+\.ixdzs8\.com/{bookid}\.zip"'
```
即 `https://down7.ixdzs8.com/{bookid}.zip`，curl 直接能下。**下完必须验证章节数/字数**——该站zip有缺章风险。

### 知轩藏书 zxcs
- 搜索：`www.zxcs.info` 首页搜索框**用浏览器输入提交**；直接拼 `/search.html?keyword=` 返回"非法参数"
- 搜索跳转到 `www.zxcs.click/{分类}/{id}.html` 书页
- 书页用 browser_console 挖真实链接：
  ```js
  Array.from(document.querySelectorAll('a')).filter(a => /下载|down|zip/i.test(a.textContent + ' ' + a.href))
  ```
  得到 `/download/{id}` → 该页面 HTML 里是第三方网盘地址（如116盘）
- 下载文件在网盘，走下面116盘流程

### 116盘（116pan.xyz）免费下载
详见 `references/116pan-captcha-download.md`。要点：
- 免费下载 = 验证码 + 10KB/s限速（21MB约40分钟）+ 6000秒间隔；"Save to Disk"要登录不限速
- **验证码是 session 绑定的**：curl 新下载的验证码 ≠ 浏览器页面显示的验证码，识别了也对不上。必须从浏览器当前页面取
- 取法：页面已加载的 captcha img → canvas.drawImage → toDataURL（页面内 fetch 和动态 new Image() 会被 CSP 阻止，但已加载 img 可以 drawImage）
- 识别：`uv run --with ddddocr python3 -c "..."`（ddddocr 对4位字母验证码可靠）

## 止损原则（用户偏好，重要）

下载流程被反爬/验证码/限速卡住超过几步时，**停下来整理下载地址直接给用户**，让他自己下。用户明确说过：费力就告诉地址，别死磕。给地址时标注：哪个是精校、文件大小、免费下载的坑（验证码/限速）。

## Pitfalls

1. ixdzs8 zip 可能缺章节 — 验证后再交付，缺章就换源
2. 116盘验证码 session 绑定 — 别用 curl 单独下载验证码
3. 长 base64 字符串复制容易漏字符 — 用 write_file 写 python 脚本拼接，别手贴到命令行
4. 知轩藏书搜索 URL 直接访问报"非法参数" — 必须走首页搜索表单

## 验证步骤

- zip 解压后数章节数（对照书页目录数）
- 抽查开头/中间/结尾章节内容完整性
- 报告给用户：文件大小、章节数、来源
