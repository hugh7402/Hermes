# LibreOffice 便携安装（免 root）

## 适用场景

文档转换流水线需要 LibreOffice 处理 .pptx → PDF/.md，但无 root 权限。

## 安装步骤

### 1. 下载 deb 包

```bash
# 推荐中科大镜像（国内快）
URL="https://mirrors.ustc.edu.cn/tdf/libreoffice/stable/26.2.4/deb/x86_64/LibreOffice_26.2.4_Linux_x86-64_deb.tar.gz"
curl -L -o libreoffice.tar.gz "$URL"
```

> ⚠️ 官方源 `download.documentfoundation.org` 国内极慢（~3KB/s），必须用镜像。

### 2. 解压并提取

```bash
tar xzf libreoffice.tar.gz
INSTALL_DIR="/opt/data/apps/libreoffice/install"
mkdir -p "$INSTALL_DIR"

for deb in LibreOffice_*/DEBS/*.deb; do
    dpkg-deb -x "$deb" "$INSTALL_DIR"
done
```

### 3. 关键发现：跳过 oosplash

`soffice` 命令通过 `oosplash` 启动，但 oosplash 依赖 X11 库（`libXinerama.so.1`），headless 模式也会报错。

**绕过方法**：直接调用 `soffice.bin`。

```bash
SOFFICE="/opt/data/apps/libreoffice/install/opt/libreoffice26.2/program/soffice.bin"
export SAL_USE_VCLPLUGIN=svp
"$SOFFICE" --headless --norestore --convert-to pdf --outdir /tmp file.pptx
```

- `SAL_USE_VCLPLUGIN=svp` — 禁用 GUI 插件，纯 headless 渲染
- `--norestore` — 跳过崩溃恢复
- `soffice.bin` 而非 `soffice` — 绕过 oosplash 的 X11 依赖

### 4. Wrapper 脚本

创建 `/opt/data/apps/libreoffice/lo_wrapper`：

```bash
#!/bin/bash
SOFFICE=/opt/data/apps/libreoffice/install/opt/libreoffice26.2/program/soffice.bin
export SAL_USE_VCLPLUGIN=svp
exec "$SOFFICE" --headless --norestore "$@"
```

## 验证

```bash
lo_wrapper --version
# LibreOffice 26.2.4.2 ...

lo_wrapper --convert-to pdf --outdir /tmp test.pptx
# convert ... -> test.pdf using filter : impress_pdf_Export
```

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `libXinerama.so.1: not found` | oosplash 需要 X11 | 用 soffice.bin 替代 |
| `exit code 81` | X11 连接失败 | 设置 `SAL_USE_VCLPLUGIN=svp` |
| AppImage URL 404 | 官方不提供 AppImage（26.x+） | 改用 deb.tar.gz |
| 下载 316 字节 | URL 错误，实际是 HTML 404 页 | 检查版本号和目录结构务必用镜像 |
