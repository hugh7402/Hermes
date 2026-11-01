# 阿里云百炼 — 笔记增强模型选择指南

记录国内百炼平台上可用于笔记增强（摘要、标签、关联）的模型定价与选择策略。

## 定价速查（中国内地，¥/百万 tokens）

| 模型 | 输入 | 输出 | 上下文窗口 | 备注 |
|------|:--:|:--:|:---:|------|
| **glm-5.1** | 6 | 24 | ≤32K | 最便宜，输入价格是另两家的 1/2 |
| **deepseek-v4-pro** | 12 | 24 | — | 均衡之选，综合能力强 |
| **qwen3.7-max** | 12 | 36 | ≤1M | 输出最贵，但推理最强、上下文最大 |
| glm-5 | 4 | 18 | ≤32K | glm-5.1 的前代，更便宜 |
| glm-4.5-air | 0.8 | 6 | ≤32K | 极低价轻量版 |

> ⚠️ 注意：qwen3.7-max 有时被误报为 ¥20/¥60，实际定价 **¥12/¥36**。以 [百炼官方模型页](https://help.aliyun.com/zh/model-studio/models) 实时数据为准。

## 单篇笔记增强成本测算

每次增强 3 次 API 调用（摘要 + 标签 + 关联），约 5000 输入 + 1500 输出 tokens：

| 模型 | 单篇 | 100篇/月 | 定位 |
|------|:--:|:--:|------|
| glm-5.1 | ¥0.066 | ¥6.6 | 🥇 日常增强首选 |
| deepseek-v4-pro | ¥0.096 | ¥9.6 | 🥈 均衡推荐 |
| qwen3.7-max | ¥0.114 | ¥11.4 | 🥉 重度/长文档专用 |

三者月费差距 < ¥5，选择更应基于**质量**而非纯价格。

## 选择策略

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| **日常笔记增强**（摘要+标签+关联） | glm-5.1 或 deepseek-v4-pro | 成本低，速度够 |
| **长文/标书/可研报告** | qwen3.7-max | 1M 上下文 + 最强推理 |
| **图片/扫描件 OCR** | qwen-vl-max 或 qwen-vl-ocr | 阿里直连，比 SiliconFlow 更稳 |
| **极低预算** | glm-4.5-air | ¥0.8/¥6，几乎免费 |

## 数据来源获取方法

阿里云百炼的定价页面是 SPA 渲染的动态页面，数据在表格中。用浏览器工具直接提取：

```javascript
// 在浏览器控制台中执行，提取所有模型定价行
(function() {
  const rows = document.querySelectorAll('tr');
  rows.forEach(row => {
    const cells = Array.from(row.querySelectorAll('td,th')).map(c => c.textContent.trim());
    if (cells.some(c => /glm-5|deepseek-v4|qwen3/.test(c))) {
      console.log(JSON.stringify({cells}));
    }
  });
})()
```

或者通过 Hermes 的 `browser_console` 工具：

```javascript
// 一步提取：找到所有目标模型的表格行
(function() {
  const rows = document.querySelectorAll('tr');
  const targetRows = [];
  rows.forEach(row => {
    const text = row.textContent.trim();
    if (/glm-5\.1|deepseek-v4-pro|qwen3\.7-max/.test(text)) {
      const cells = Array.from(row.querySelectorAll('td,th')).map(c => c.textContent.trim());
      targetRows.push({cells, text: text.substring(0, 300)});
    }
  });
  return targetRows;
})()
```

## 已知问题

- **BAILIAN_API_KEY 截断**：`.env` 中 `BAILIAN_API_KEY` 可能被 Hermes 凭证存储截断为 9 字符（`sk-929...`）。如果出现 401 错误，让用户重新提供 Key。
- **SiliconFlow vs Bailian 视觉模型**：图片识别推荐百炼直连（qwen-vl-max），延迟更低且无 GFW 问题。SiliconFlow 的 Qwen3-VL-8B 作为备选。
