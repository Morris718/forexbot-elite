# ============================================================
#  FOREX TRADING BOT - COMPLETE LAUNCHER
# ============================================================

$ProjectPath = "C:\Users\user\OneDrive\Desktop\Forex_trading_bot"
$NgrokToken = "3DvxX0KYoKhDiVJ3HlP70sQeiv7_7GGAX5v1ub2E69EndMENq"
$MpesaConsumerKey = "tLhEndkero1L0GxFHpRhyCL13YpmlBGF2lD6t4cn9UtEtifi"
$MpesaConsumerSecret = "LwTOEKLxQIAdGVl8kjXGfGskYdKflUlcLMrnxIdG06x0zIL0QrFneF6izArmK08l"

Set-Location $ProjectPath

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host "    FOREX TRADING BOT - FULL SYSTEM LAUNCHER" -ForegroundColor Cyan
Write-Host "    M-Pesa + Ngrok + Flask + Trading Bot" -ForegroundColor Cyan
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host ""

# STEP 1: Verify Project
Write-Host "[STEP 1/6] Verifying Environment..." -ForegroundColor Yellow
if (-not (Test-Path "app.py")) {
    Write-Host "  ERROR: app.py NOT FOUND" -ForegroundColor Red
    exit
}
Write-Host "  OK - Project verified" -ForegroundColor Green
Write-Host ""

# STEP 2: Update .env
Write-Host "[STEP 2/6] Configuring .env..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Copy-Item ".env" ".env.backup" -Force
}

$envContent = if (Test-Path ".env") { Get-Content ".env" } else { @() }
$envContent = $envContent | Where-Object { $_ -notmatch '^MPESA_' -and $_ -notmatch '^# ====.*M-PESA' }
$envContent | Set-Content ".env"

@"

# ============ M-PESA DARAJA API ============
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=$MpesaConsumerKey
MPESA_CONSUMER_SECRET=$MpesaConsumerSecret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://placeholder.ngrok-free.app/payments/mpesa/callback
"@ | Add-Content -Path ".env"

Write-Host "  OK - .env configured" -ForegroundColor Green
Write-Host ""

# STEP 3: Configure ngrok
Write-Host "[STEP 3/6] Setting up ngrok..." -ForegroundColor Yellow

if (-not (Test-Path ".\ngrok.exe")) {
    Write-Host "  ERROR: ngrok.exe NOT FOUND" -ForegroundColor Red
    exit
}

.\ngrok.exe config add-authtoken $NgrokToken 2>&1 | Out-Null
Write-Host "  OK - Authtoken configured" -ForegroundColor Green
Write-Host ""

# STEP 4: Start ngrok
Write-Host "[STEP 4/6] Starting ngrok tunnel..." -ForegroundColor Yellow
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectPath'; Write-Host 'NGROK TUNNEL' -ForegroundColor Cyan; .\ngrok.exe http 5000"
Write-Host "  Waiting 8 seconds for ngrok..." -ForegroundColor DarkGray
Start-Sleep -Seconds 8
Write-Host "  OK - ngrok started" -ForegroundColor Green
Write-Host ""

# STEP 5: Fetch ngrok URL
Write-Host "[STEP 5/6] Fetching ngrok URL..." -ForegroundColor Yellow

$retries = 8
$ngrokUrl = $null

for ($i = 1; $i -le $retries; $i++) {
    try {
        $ngrokInfo = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -ErrorAction Stop
        $ngrokUrl = $ngrokInfo.tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -First 1 -ExpandProperty public_url
        if ($ngrokUrl) {
            Write-Host "  OK - URL: $ngrokUrl" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  Attempt $i/$retries..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
}

if (-not $ngrokUrl) {
    Write-Host "  ERROR: Could not get ngrok URL" -ForegroundColor Red
    Write-Host "  Check ngrok window for errors" -ForegroundColor Yellow
    exit
}

$callbackUrl = "$ngrokUrl/payments/mpesa/callback"
(Get-Content .env) -replace 'MPESA_CALLBACK_URL=.*', "MPESA_CALLBACK_URL=$callbackUrl" | Set-Content .env
Write-Host "  OK - Callback URL set" -ForegroundColor Green
Write-Host ""

# STEP 6: Display info and launch
Write-Host "[STEP 6/6] Launching Flask App..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "    ALL SYSTEMS READY!" -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  ACCESS URLS:" -ForegroundColor Cyan
Write-Host "    Local App      : http://localhost:5000" -ForegroundColor White
Write-Host "    Public URL     : $ngrokUrl" -ForegroundColor White
Write-Host "    Admin Login    : http://localhost:5000/admin/login" -ForegroundColor White
Write-Host "    M-Pesa Deposit : http://localhost:5000/payments/mpesa/deposit" -ForegroundColor White
Write-Host "    Ngrok Inspector: http://127.0.0.1:4040" -ForegroundColor White
Write-Host ""
Write-Host "  M-PESA TEST CREDENTIALS:" -ForegroundColor Yellow
Write-Host "    Phone Number   : 254708374149" -ForegroundColor White
Write-Host "    Amount         : 1 KES" -ForegroundColor White
Write-Host "    M-Pesa PIN     : 1234" -ForegroundColor White
Write-Host ""
Write-Host "  ADMIN LOGIN:" -ForegroundColor Magenta
Write-Host "    Email          : mutindamorris718@gmail.com" -ForegroundColor White
Write-Host "    Password       : Admin@123" -ForegroundColor White
Write-Host ""
Write-Host "  Starting Flask in 3 seconds... (Press Ctrl+C to stop)" -ForegroundColor Cyan
Start-Sleep -Seconds 3

python app.py
