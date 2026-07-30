# Dang ky webhook Zalo / Telegram cho BHI Agent
# Chay sau khi da co PUBLIC_BASE_URL va token trong .env

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".env")) {
    Write-Error "Thieu file .env — copy tu .env.example"
}

Write-Host "=== SETUP MESSAGING WEBHOOKS ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Can co trong .env:" -ForegroundColor Yellow
Write-Host "  PUBLIC_BASE_URL=https://your-domain.com"
Write-Host "  TELEGRAM_BOT_TOKEN=...  (tu @BotFather)"
Write-Host "  ZALO_OA_ACCESS_TOKEN=... (tu Zalo Developers)"
Write-Host ""

python scripts/setup_messaging_webhooks.py

Write-Host ""
Write-Host "Huong dan them:" -ForegroundColor Green
Write-Host "  1. Copy data/messaging_links.example.json -> data/messaging_links.json"
Write-Host "  2. Nhan vien nhan tin bot -> lay telegram_chat_id / zalo_user_id"
Write-Host "  3. Dien vao messaging_links.json (map email nhan su)"
Write-Host "  4. GET /api/messaging/status de kiem tra"
