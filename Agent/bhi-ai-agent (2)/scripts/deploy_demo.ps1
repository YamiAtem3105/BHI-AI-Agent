# Deploy demo with public URL - sets PUBLIC_BASE_URL so OAuth won't redirect to localhost
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Port = 8000
$HealthUrl = "http://127.0.0.1:$Port/health"

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

if (-not (Test-Path ".\data\staff.json")) {
    Write-Error "Missing data/staff.json"
}

Remove-Item "cloudflared-demo.log", "cloudflared-demo.err.log" -ErrorAction SilentlyContinue
Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:$Port" `
    -RedirectStandardOutput "cloudflared-demo.log" `
    -RedirectStandardError "cloudflared-demo.err.log" `
    -WorkingDirectory $Root -WindowStyle Hidden | Out-Null

Start-Sleep -Seconds 5
$PublicUrl = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    $log = Get-Content "cloudflared-demo.err.log" -Raw -ErrorAction SilentlyContinue
    if ($log -match '(https://[a-z0-9-]+\.trycloudflare\.com)') {
        $PublicUrl = $Matches[1]
        break
    }
}
if (-not $PublicUrl) {
    Write-Error "Cannot get tunnel URL. See cloudflared-demo.err.log"
}
$env:PUBLIC_BASE_URL = $PublicUrl
$env:PYTHONIOENCODING = "utf-8"

Write-Host "PUBLIC_BASE_URL = $PublicUrl" -ForegroundColor Cyan

Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "$Port" `
    -WorkingDirectory $Root -WindowStyle Hidden | Out-Null

Start-Sleep -Seconds 4
Invoke-RestMethod $HealthUrl | Out-Null

# Smoke test public URL (health + login + chat + dashboard)
Write-Host "Running smoke test..." -ForegroundColor Cyan
$test = & ".\.venv\Scripts\python.exe" -c @"
import httpx, sys
b='$PublicUrl'
try:
    assert httpx.get(f'{b}/health', timeout=15).json()['status']=='ok'
    r=httpx.post(f'{b}/api/login', json={'email':'nosdevai2k@gmail.com','password':'TestPass123!'}, timeout=15).json()
    assert r.get('success') and r.get('token')
    h={'Authorization':'Bearer '+r['token']}
    assert httpx.post(f'{b}/api/chat', json={'message':'xin chao'}, headers=h, timeout=30).json().get('response')
    assert httpx.get(f'{b}/api/dashboard', headers=h, timeout=15).status_code==200
    for p in ['/', '/dashboard', '/admin/']:
        assert httpx.get(f'{b}{p}', timeout=15).status_code==200
    print('PASS')
except Exception as e:
    print('FAIL', e); sys.exit(1)
"@
if ($LASTEXITCODE -ne 0) { Write-Error "Smoke test failed: $test" }
Write-Host "Smoke test: $test" -ForegroundColor Green

Write-Host ""
Write-Host "=== BHI AI Agent DEMO LIVE ===" -ForegroundColor Green
Write-Host "Chat      : $PublicUrl/"
Write-Host "Dashboard : $PublicUrl/dashboard"
Write-Host "Admin     : $PublicUrl/admin/"
Write-Host "OAuth CB  : $PublicUrl/auth/google/callback"
Write-Host ""
Write-Host "=== GOOGLE OAUTH (fix redirect_uri_mismatch) ===" -ForegroundColor Yellow
Write-Host "Them URI sau vao Google Cloud Console > OAuth Client > Authorized redirect URIs:"
Write-Host "  $PublicUrl/auth/google/callback" -ForegroundColor White
Write-Host "  http://localhost:8000/auth/google/callback  (dev local)"
Write-Host "Link: https://console.cloud.google.com/auth/clients"
Write-Host ""
Write-Host "For fixed URL (no local PC): run scripts/deploy_render.ps1"
