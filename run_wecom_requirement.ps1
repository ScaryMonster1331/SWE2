param(
    [Parameter(Mandatory = $true)]
    [string]$ApprovalId,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$arguments = @(
    "-m", "sweagent", "requirements", "process",
    "--approval-id", $ApprovalId
)
if ($DryRun) {
    $arguments += "--dry-run"
}

& "$PSScriptRoot\.venv\Scripts\python.exe" @arguments
exit $LASTEXITCODE
