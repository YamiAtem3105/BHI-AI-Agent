# Huong dan deploy Render (URL co dinh, khong phu thuoc may local)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host ""
Write-Host "=== DEPLOY BHI AI AGENT LEN RENDER (URL co dinh) ===" -ForegroundColor Green
Write-Host ""
Write-Host "1. Push code len GitHub (branch main)"
Write-Host "2. Vao https://dashboard.render.com -> New -> Blueprint"
Write-Host "3. Connect repo: Nos-hash/bhi-ai-agent"
Write-Host "4. Chon render.yaml -> Apply"
Write-Host "5. Vao Environment, them cac bien sau:"
Write-Host "   - OPENAI_API_KEY"
Write-Host "   - GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (neu dung OAuth)"
Write-Host "   - PUBLIC_BASE_URL = https://<ten-service>.onrender.com (sau deploy lan dau)"
Write-Host "   - STAFF_JSON_B64 / PERSONAL_JSON_B64 (chay scripts/encode_deploy_secrets.ps1)"
Write-Host ""
Write-Host "6. Google Cloud Console -> OAuth redirect URI:"
Write-Host "   https://<ten-service>.onrender.com/auth/google/callback"
Write-Host ""
Write-Host "URL demo se co dang: https://bhi-ai-agent.onrender.com"
Write-Host ""

& "$Root\scripts\encode_deploy_secrets.ps1"
