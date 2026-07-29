# aria2 Bash 包装器并行下载（2026-07-09 新增）

## 问题：`--input-file` 与长 CDN URL 不兼容

PikPak CDN URL 约 835 字符，包含大量 query parameters。`--input-file` 解析长 URL 时可能截断或混淆：

```bash
# ❌ 不靠谱 — URL 中包含 &、?、= 等特殊字符，input-file 解析出错
# 报错：total length mismatch. expected: 6429096397, actual: 7395207885
/opt/data/aria2c --input-file=/tmp/urls.txt
```

## 方案：Bash 包装器 + 变量传参

将 URL 读入 shell 变量，作为命令行参数直接传递：

```bash
#!/bin/bash
export LD_LIBRARY_PATH=/opt/data

# 读取 URL 到变量
SONE_URL=$(cat /tmp/SONE-028-UC_cdn.txt)
DRPT_URL=$(cat /tmp/DRPT-109_cdn.txt)
DSOD_URL=$(cat /tmp/DSOD-008_cdn.txt)

# 后台启动三个 aria2 实例（并行）
/opt/data/aria2c -x 8 --continue=true --dir=/tmp/dl --out='SONE-028-UC.mp4' "$SONE_URL" &
PID1=$!
/opt/data/aria2c -x 8 --continue=true --dir=/tmp/dl --out='DRPT-109.mp4' "$DRPT_URL" &
PID2=$!
/opt/data/aria2c -x 8 --continue=true --dir=/tmp/dl --out='DSOD-008.mp4' "$DSOD_URL" &
PID3=$!

wait $PID1 $PID2 $PID3
echo "ALL DONE"
```

## 使用场景

- **3-5 个文件并行下载**：每个文件独立 aria2 进程，互不干扰
- **CDN URL 需要从文件读取**：因为 URL 太长无法直接硬编码在 shell 命令里
- **需要在脚本内 export LD_LIBRARY_PATH**：确保每个子进程都能找到 libaria2.so.0

## 注意事项

1. URL 变量必须用双引号 `"$URL"` 包裹，防止 shell 分词
2. `LD_LIBRARY_PATH` 需要在脚本内或 `export` 后生效，前缀式也行但需要每个命令单独写
3. 用 `wait $PID1 $PID2 $PID3` 等待全部完成，不设超时
4. 每个 aria2 实例使用独立的 `--out` 参数避免文件名冲突
5. CDN URL 可能几分钟内就过期（403 错误），**必须在启动下载前立即获取**，不能缓存后等很久再用
