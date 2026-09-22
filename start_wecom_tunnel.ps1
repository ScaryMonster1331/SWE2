$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Remove-Item Env:ALL_PROXY,Env:GIT_HTTP_PROXY,Env:GIT_HTTPS_PROXY,Env:HTTP_PROXY,Env:HTTPS_PROXY -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\requirements" | Out-Null

$callbackPort = Get-NetTCPConnection -State Listen -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($callbackPort) {
    Stop-Process -Id $callbackPort.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}
Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\python.exe" -ArgumentList "$PSScriptRoot\wecom_callback_server.py" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$PSScriptRoot\requirements\callback.out.log" -RedirectStandardError "$PSScriptRoot\requirements\callback.err.log" | Out-Null
Start-Sleep -Seconds 2

$log = "$PSScriptRoot\requirements\cloudflared.log"
$err = "$PSScriptRoot\requirements\cloudflared.err.log"
$cloudflaredExe = Join-Path $PSScriptRoot "tools\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflaredExe)) {
    & "$PSScriptRoot\install_cloudflared.ps1"
}
$cloudflared = Get-Process cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    Start-Process -FilePath $cloudflaredExe -ArgumentList "tunnel", "--url", "http://127.0.0.1:5000", "--no-autoupdate" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err | Out-Null
}

$url = $null
for ($i = 0; $i -lt 30 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    $text = ((Get-Content -LiteralPath $log -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath $err -ErrorAction SilentlyContinue)) -join "`n"
    $url = [regex]::Match($text, "https://[a-zA-Z0-9-]+\.trycloudflare\.com").Value
}

if (-not $url) {
    throw "未能获取 Cloudflare Tunnel URL，请查看 requirements\cloudflared.err.log"
}

Write-Host "企业微信接收消息服务器URL:"
Write-Host "$url/wecom/callback"



