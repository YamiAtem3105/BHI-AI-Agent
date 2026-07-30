# Thiết lập Google OAuth cho BHI Agent — chạy: .\scripts\setup_google_oauth.ps1
# KHÔNG commit Client Secret. File .env đã nằm trong .gitignore.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$EnvFile = Join-Path $ProjectRoot ".env"
$RedirectUri = "http://localhost:8000/auth/google/callback"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BHI Agent — Thiết lập Google OAuth" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Bước 1: Mở Google Cloud Console (đăng nhập Gmail công ty/cá nhân của bạn)" -ForegroundColor Yellow
Write-Host "  Link Credentials: https://console.cloud.google.com/apis/credentials"
Write-Host "  Link OAuth Clients (mới): https://console.cloud.google.com/auth/clients"
Write-Host ""

$open = Read-Host "Mở trình duyệt tới trang Credentials? (Y/n)"
if ($open -ne "n" -and $open -ne "N") {
    Start-Process "https://console.cloud.google.com/auth/clients"
}

Write-Host ""
Write-Host "Bước 2: Làm theo trên Google Cloud Console" -ForegroundColor Yellow
Write-Host @"
  A) Chọn hoặc tạo Project (vd: BHI-Agent)
  B) Nếu được hỏi 'Configure consent screen':
     - User Type: External (hoặc Internal nếu có Google Workspace công ty)
     - App name: BHI Agent
     - User support email: email của bạn
     - Developer contact: email của bạn
     - Scopes: giữ mặc định (openid, email, profile là đủ)
     - Test users: thêm Gmail nhân viên sẽ đăng nhập thử
  C) Create Credentials > OAuth client ID (hoặc nút Create Client)
     - Application type: Web application
     - Name: BHI Agent Local
     - Authorized redirect URIs — copy CHÍNH XÁC dòng sau:
       $RedirectUri
  D) Sau khi Create, copy Client ID và Client Secret (secret chỉ hiện 1 lần!)
"@ -ForegroundColor Gray

Write-Host ""
Write-Host "Bước 3: Dán credential vào đây (input ẩn với Secret)" -ForegroundColor Yellow

$clientId = Read-Host "GOOGLE_CLIENT_ID (dạng xxx.apps.googleusercontent.com)"
if (-not $clientId -or $clientId -notmatch "apps\.googleusercontent\.com") {
    Write-Host "Client ID không hợp lệ. Phải chứa .apps.googleusercontent.com" -ForegroundColor Red
    exit 1
}

$secure = Read-Host "GOOGLE_CLIENT_SECRET" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$clientSecret = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if (-not $clientSecret -or $clientSecret.Length -lt 8) {
    Write-Host "Client Secret quá ngắn hoặc trống." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Write-Host "Không tìm thấy .env — copy từ .env.example trước." -ForegroundColor Red
    exit 1
}

$lines = Get-Content $EnvFile -Encoding UTF8
$keys = @{
    "GOOGLE_CLIENT_ID"      = $clientId.Trim()
    "GOOGLE_CLIENT_SECRET"  = $clientSecret.Trim()
    "GOOGLE_REDIRECT_URI"   = $RedirectUri
}
$seen = @{}
$out = foreach ($line in $lines) {
    if ($line -match "^([A-Z_]+)=") {
        $k = $Matches[1]
        if ($keys.ContainsKey($k)) {
            $seen[$k] = $true
            "$k=$($keys[$k])"
            continue
        }
    }
    $line
}
foreach ($k in $keys.Keys) {
    if (-not $seen[$k]) { $out += "$k=$($keys[$k])" }
}
Set-Content -Path $EnvFile -Value $out -Encoding UTF8

Write-Host ""
Write-Host "Da luu vao .env (khong hien thi secret)." -ForegroundColor Green

Write-Host ""
Write-Host "Bước 4: Kiem tra..." -ForegroundColor Yellow
Push-Location $ProjectRoot
& .\.venv\Scripts\python -c @"
from app.config import settings
ok = bool(settings.google_client_id and settings.google_client_secret)
print('OAuth configured:', ok)
print('Redirect URI:', settings.google_redirect_uri)
if not ok:
    raise SystemExit(1)
"@
$pyOk = $LASTEXITCODE -eq 0
Pop-Location

if ($pyOk) {
    Write-Host ""
    Write-Host "XONG! Restart server roi mo: http://127.0.0.1:8000/" -ForegroundColor Green
    Write-Host "Nut 'Dang nhap bang Google' se hien khi OAuth da cau hinh." -ForegroundColor Green
} else {
    Write-Host "Kiem tra that bai — xem lai .env" -ForegroundColor Red
    exit 1
}
