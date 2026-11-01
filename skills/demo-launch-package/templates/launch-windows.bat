@echo off
REM 启动脚本（Windows）· 保存时必须是 GBK 编码 + CRLF 行尾，否则中文控制台乱码
chcp 936 >nul
title 系统演示启动包
echo.
cd /d "%~dp0"

if not exist "index.html" (
  echo [错误] 同目录下没有 index.html
  echo.
  pause
  exit /b 1
)
if not exist "serve.ps1" (
  echo [错误] 同目录下没有 serve.ps1
  echo.
  pause
  exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
  echo [错误] 本机没有 Windows PowerShell，无法启动本地服务。
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo   正在启动本地服务，请稍候（首次启动约 1-2 秒）...
echo   地址栏将显示：http://localhost:8080/
echo   结束使用：关闭浏览器窗口后，回到本窗口按 Ctrl+C
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1" -Port 8080

echo.
echo 服务已停止。
pause
