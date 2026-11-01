# 反图识别女优（靠画面匹配，不靠人脸，2026-10-19 实测）

用户发来几张 JAV 截图问"她叫什么"。**不要凭脸猜名字**（用户铁律：女优名/描述不许擅猜）。
唯一可走的路：画面匹配 → 番号 → javdb 查女优。

## 各引擎实测

| 引擎 | 结果 | 备注 |
|---|---|---|
| **Yandex 反图（URL 方式）** | ✅ 唯一可用 | 见下方配方 |
| Yandex 浏览器上传 | ❌ SmartCaptcha | 无头浏览器被识别，换出口节点也没用 |
| Google Lens | ❌ 风控/账号关联 | 提示"图片未与账号关联"；走代理还要过 `sorry/index` |
| TinEye | ❌ 0 命中 | 不爬这类站 |
| 百度识图 | ❌ 只出相似商品 | 会推内衣/海报 |
| Bing 视觉搜索 | ❌ 拿不到 file input | `cn.bing.com/visualsearch` 退回首页 |

## 可用配方（curl，无 JS 所以无验证码）

1. 图挂临时图床（**属外传，先经用户同意**）：
   `curl -F reqtype=fileupload -F time=1h -F fileToUpload=@img.png https://litterbox.catbox.moe/resources/internals/api.php`
   → 返回 `https://litter.catbox.moe/xxxx.png`（1 小时自动失效）。⚠️ 0x0.st 已关闭上传。
2. `curl -x http://127.0.0.1:10808 -A "<desktop UA>" \
   "https://yandex.com/images/search?rpt=imageview&url=<urlencode(公网URL)>"`。
   **必须走代理**：直连返回 "The service is under construction"（地理屏蔽）。
3. 解析返回 HTML：`\b([A-Z]{2,6})[-_ ]?(\d{2,5})\b` 统计番号频次，取前 3 名喂 javdb。
   JSON 里斜杠是 `\/`，取站点 URL 前先 `.replace('\\/','/')`。
4. javdb（同一个代理）搜番号 → 详情页 `href="/actors/<id>"`（过滤掉 有碼/無碼/歐美 三个导航项）。

## 可信度判定（这步不能省）

- Yandex 命中次数**断崖领先**（如 29 次 vs 第二名 8 次）才可说"最可能"，且只能说**最可能**。
- 帧级复核：详情页取封面 id（`https://c0.jdbstatic.com/covers/xx/<id>.jpg`），再抓
  `https://c0.jdbstatic.com/samples/xx/<id>_s_N.jpg` 直到 404，与截图做归一化互相关
  （裁掉边缘 6% 去水印 → 320×180 灰度 → 零均值单位方差）。
  **实测：正确的番号也只有 +0.2~0.33**（样张几张到十几张，覆盖不到那一帧）→
  **帧级比对只能排除，不能确认**，别把 +0.3 说成"就是这部"。
- 交付话术：给「最可能 + 候选 + 置信度低」三档，并说明 100% 定案需用户给番号或下正片抽帧比对。

## 附带线索

截图右上角 `IPPA` + 6 位审查号 + 圆形字母 Logo 是厂牌线索（M=Madonna、HBAD=HIBINO），
可交叉验证：候选若全落在同一厂牌，说明画面方向判断没错。三张图女优发型/体型明显不同时，
要提醒用户按单个人分别给番号，别混着查。
