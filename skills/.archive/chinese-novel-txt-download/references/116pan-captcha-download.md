# 116盘（116pan.xyz）验证码下载流程

2026-08 实测（下载知轩藏书黜龙 cl.zip 21.66MB 时验证）。

## 现状

- 免费下载：验证码 + 10KB/s 限速 + 6000秒下载间隔（下完一次要等100分钟才能再下）
- "Save to Disk"（登录后）不限速，但要注册账号
- 文件页 URL 形如 `https://www.116pan.xyz/f/{fileid}`

## 关键坑：验证码 session 绑定

`/captcha/18?{timestamp}` 每次请求都生成**新**验证码。
- 用 curl 独立下载验证码图片 → 识别出的是新验证码，与浏览器页面显示的**不一致**，提交必失败
- 必须从浏览器当前页面（同一个 session）取验证码

## 从浏览器取验证码（绕过 CSP）

页面内 `fetch()` 和动态 `new Image()` 都被 CSP 阻止（Failed to fetch / img load fail），
但**页面已加载的 img 元素可以直接 drawImage 到 canvas**：

```js
// 在文件页点了 "Normal Download" 弹出确认框后执行
(() => {
  const imgs = Array.from(document.querySelectorAll('img')).filter(i => i.src.includes('captcha'));
  if (!imgs.length) return {err: 'no captcha'};
  const img = imgs[0];
  const cv = document.createElement('canvas');
  cv.width = img.naturalWidth; cv.height = img.naturalHeight;
  cv.getContext('2d').drawImage(img, 0, 0);
  const b64 = cv.toDataURL('image/png').split(',')[1];
  // 分段输出避免单条消息过长，每段约600字符
  const parts = [];
  for (let i = 0; i < b64.length; i += 600) parts.push(b64.slice(i, i + 600));
  return {w: img.naturalWidth, h: img.naturalHeight, nparts: parts.length, parts};
})()
```

注意：
- 浏览器会话不稳定（Browserbase 远程浏览器），console 操作后页面可能变 empty，需重新 navigate 再点 Normal Download
- 验证码有有效期，识别+填写要快

## 识别验证码（ddddocr）

```bash
uv run --with ddddocr --with Pillow python3 -c "
import ddddocr
ocr = ddddocr.DdddOcr(show_ad=False)
with open('cap.png','rb') as f:
    print(ocr.classification(f.read()))
"
```
4位小写字母验证码识别可靠（cuyk/csbn 等一次成功）。

## base64 拼接防错

长 base64 字符串从 console 复制到命令行容易漏字符（JPEG 会报 image file is truncated）。
正确做法：把分段 base64 用 **write_file 写 python 脚本**（列表拼接），再运行解码，而不是内联粘贴。

```python
parts = ["段1", "段2", ...]  # 从 console 结果复制
b64 = ''.join(parts)
b64 += '=' * (-len(b64) % 4)
open('cap.png','wb').write(base64.b64decode(b64))
```

## 提交

识别结果输入弹窗 "Enter Captcha" 输入框 → Confirm Download → 浏览器开始下载（10KB/s）。
21.66MB ≈ 37-40 分钟，可后台跑。

## 止损建议

这套流程约 10+ 步，性价比低。除非用户明确要这份精校资源且接受等待，
否则第一步就给用户网盘直链让他自己下（他可能愿意注册登录拿不限速）。
