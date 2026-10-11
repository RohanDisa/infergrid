# Windows entrypoint for Phase 0. Requires Docker Desktop, kind, helm, kubectl.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:CLUSTER = if ($env:CLUSTER) { $env:CLUSTER } else { "infergrid" }

Write-Host "==> building images"
docker build -t infergrid/gateway:dev gateway
docker build -t infergrid/mock-backend:dev mock-backend

if (Get-Command bash -ErrorAction SilentlyContinue) {
    bash infra/local/up.sh
    return
}

Write-Host "bash not found. Install Git Bash or WSL, then re-run, or execute infra/local/up.sh from a Unix shell."
exit 1
