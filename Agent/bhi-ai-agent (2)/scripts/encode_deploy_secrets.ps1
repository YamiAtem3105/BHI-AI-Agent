# Sinh base64 cho Render env vars (staff.json + personal data — không commit lên git)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$staff = Join-Path $Root "data\staff.json"
$personal = Join-Path $Root "data\personal\phan_minh_hoang.json"

if (-not (Test-Path $staff)) { Write-Error "Thieu data/staff.json" }

$staffB64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($staff))
Write-Host "STAFF_JSON_B64 ($([math]::Round($staffB64.Length/1024,1)) KB):" -ForegroundColor Cyan
Write-Host $staffB64
Write-Host ""

if (Test-Path $personal) {
    $personalB64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($personal))
    Write-Host "PERSONAL_JSON_B64 ($([math]::Round($personalB64.Length/1024,1)) KB):" -ForegroundColor Cyan
    Write-Host $personalB64
    Write-Host ""
}

Write-Host "Dan vao Render Dashboard > bhi-ai-agent > Environment" -ForegroundColor Yellow
