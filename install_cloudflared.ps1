$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$targetDir = Join-Path $PSScriptRoot "tools\cloudflared"
$target = Join-Path $targetDir "cloudflared.exe"
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
if (Test-Path $target) {
    & $target --version
    exit $LASTEXITCODE
}
$url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
Write-Host "Downloading cloudflared from $url"
Invoke-WebRequest -Uri $url -OutFile $target
& $target --version
