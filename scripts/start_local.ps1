param(
    [switch]$RebuildData
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendLog = Join-Path $env:TEMP "racequant-backend.out.log"
$BackendErr = Join-Path $env:TEMP "racequant-backend.err.log"
$FrontendLog = Join-Path $env:TEMP "racequant-frontend.out.log"
$FrontendErr = Join-Path $env:TEMP "racequant-frontend.err.log"

function Get-ListenerPid {
    param([int]$Port)
    $Connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $Connection) {
        return $null
    }
    return $Connection.OwningProcess
}

if ($RebuildData) {
    python (Join-Path $Root "scripts\build_local_data.py") --source auto --reset
}

Remove-Item -LiteralPath $BackendLog, $BackendErr, $FrontendLog, $FrontendErr -ErrorAction SilentlyContinue

$BackendPid = Get-ListenerPid -Port 8000
$BackendStatus = "existing"
if ($null -eq $BackendPid) {
    $Backend = Start-Process `
        -FilePath "powershell.exe" `
        -WindowStyle Hidden `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErr `
        -PassThru `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "cd '$Root'; `$env:PYTHONPATH='$Root\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
        )
    $BackendPid = $Backend.Id
    $BackendStatus = "started"
}

$FrontendPid = Get-ListenerPid -Port 5173
$FrontendStatus = "existing"
if ($null -eq $FrontendPid) {
    $Frontend = Start-Process `
        -FilePath "cmd.exe" `
        -WindowStyle Hidden `
        -WorkingDirectory (Join-Path $Root "frontend") `
        -RedirectStandardOutput $FrontendLog `
        -RedirectStandardError $FrontendErr `
        -PassThru `
        -ArgumentList @("/c", "npm run dev -- --host 127.0.0.1")
    $FrontendPid = $Frontend.Id
    $FrontendStatus = "started"
}

Start-Sleep -Seconds 4

$BackendHealth = try {
    Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 5 | ConvertTo-Json -Compress
} catch {
    "FAILED: $($_.Exception.Message)"
}

$FrontendHealth = try {
    (Invoke-WebRequest "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 5).StatusCode
} catch {
    "FAILED: $($_.Exception.Message)"
}

[pscustomobject]@{
    BackendUrl = "http://127.0.0.1:8000"
    BackendPid = $BackendPid
    BackendStatus = $BackendStatus
    BackendHealth = $BackendHealth
    BackendLog = $BackendLog
    FrontendUrl = "http://127.0.0.1:5173"
    FrontendPid = $FrontendPid
    FrontendStatus = $FrontendStatus
    FrontendHealth = $FrontendHealth
    FrontendLog = $FrontendLog
}
