# 静态服务（Windows / PowerShell）+ 单页回退 —— 保存时必须 UTF-8 带 BOM（PS 5.1 才认中文）
# 只监听 127.0.0.1；用 TcpListener 而非 HttpListener —— 后者在部分机器上需要管理员权限
param([int]$Port = 8080)

$ErrorActionPreference = 'Stop'
$root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$index = Join-Path $root 'index.html'

# 选一个可用端口
$listener = $null
for ($p = $Port; $p -lt ($Port + 20); $p++) {
    try {
        $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $p)
        $l.Start(); $listener = $l; $Port = $p; break
    } catch { }
}
if ($null -eq $listener) { Write-Host '启动失败：找不到可用端口。'; exit 1 }

$url = "http://localhost:$Port/"
Write-Host "服务已启动：$url"

# 打开浏览器（普通窗口＝地址栏可见；--app= 隐藏地址栏，--kiosk= 全屏；独立配置不带出个人书签）
$candidates = @()
if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe') }
if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe') }
if ($env:LOCALAPPDATA) { $candidates += (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe') }
$chrome = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
$homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$profileDir = Join-Path $homeDir '.drs-chrome'
try {
    if ($chrome) {
        Start-Process -FilePath $chrome -ArgumentList @(
            "--user-data-dir=$profileDir", '--no-first-run', '--no-default-browser-check',
            '--new-window', $url) | Out-Null
        Write-Host "已用 Chrome 打开：$url"
    } else {
        Start-Process $url | Out-Null
        Write-Host "未找到 Chrome，已用默认浏览器打开：$url"
    }
} catch {
    Write-Host "（自动打开浏览器失败，请手动在浏览器中访问：$url）"
}
Write-Host '结束使用：先关闭浏览器窗口，再回到本窗口按 Ctrl+C 停止服务。'

$mime = @{
    '.html'='text/html; charset=utf-8'; '.js'='application/javascript; charset=utf-8'
    '.css'='text/css; charset=utf-8';  '.json'='application/json; charset=utf-8'
    '.png'='image/png'; '.jpg'='image/jpeg'; '.svg'='image/svg+xml'; '.ico'='image/x-icon'
    '.csv'='text/csv; charset=utf-8'; '.txt'='text/plain; charset=utf-8'
}

Write-Host '服务运行中（Ctrl+C 停止）…'
try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        try {
            $stream = $client.GetStream(); $stream.ReadTimeout = 3000
            $buf = New-Object byte[] 8192
            $n = 0
            try { $n = $stream.Read($buf, 0, $buf.Length) } catch { $n = 0 }
            $raw = [System.Text.Encoding]::ASCII.GetString($buf, 0, [Math]::Max($n, 0))
            $reqPath = '/'
            $m = [regex]::Match($raw, '^[A-Za-z]+\s+(\S+)')
            if ($m.Success) { $reqPath = $m.Groups[1].Value }
            $reqPath = [System.Uri]::UnescapeDataString(($reqPath -split '\?')[0]).TrimStart('/')

            $file = $index
            if ($reqPath -ne '' -and $reqPath -notmatch '\.\.') {      # 拦目录穿越
                $cand = Join-Path $root $reqPath
                if (Test-Path $cand -PathType Leaf) { $file = $cand }
            }
            $bytes = [System.IO.File]::ReadAllBytes($file)
            $ext = [System.IO.Path]::GetExtension($file).ToLower()
            $ctype = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { 'text/html; charset=utf-8' }
            $head = "HTTP/1.1 200 OK`r`nContent-Type: $ctype`r`nContent-Length: $($bytes.Length)" +
                    "`r`nCache-Control: no-store`r`nConnection: close`r`n`r`n"
            $hb = [System.Text.Encoding]::ASCII.GetBytes($head)
            $stream.Write($hb, 0, $hb.Length)
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.Flush()
        } catch { }
        finally { try { $client.Close() } catch { } }
    }
} finally {
    try { $listener.Stop() } catch { }
}
