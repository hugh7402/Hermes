# 批量补增强（bulk repair）

当大量笔记因 API 欠费、网络中断、内容过滤（400）等原因未完成增强时，
用 `/opt/data/bulk_enhance.py` 批量扫描并补处理。

## 触发条件

```bash
# 查看未增强数量
find concepts/ -name "*.md" -exec grep -L "^tags:" {} \; | wc -l
```

如果 > 0，运行：

```bash
python3 /opt/data/bulk_enhance.py
```

## 工作原理

1. 扫描 `concepts/` 下所有 .md 文件
2. 检测 frontmatter 中是否含 `tags:`（只搜前 500 字符）
3. 对缺失者调用 `note_enhance.py` 单文件增强
4. 每个文件最多 300s，超时则跳过
5. 输出成功/失败计数

## 常见失败原因

| 症状 | 原因 | 对策 |
|------|------|------|
| HTTP 400 | 敏感词触发内容审核 | 换 deepseek-v4-pro |
| TimeoutExpired | GLM-5.1 偶发慢 | 自动跳过，再次运行可重试 |
| 401 Unauthorized | 欠费 | 提醒用户充值后重跑 |

## 注意事项

- 输出缓冲到 stdout，不实时打印。用 `find concepts/ -exec grep -l "^tags:"` 观察进度
- 处理 219 篇约需 2.5 小时（每篇 ~40s）
- 幂等：已增强的不会重复处理
