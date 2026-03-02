# =============================================================================
# TVI Pčela — deploy na server
# Pokretanje: powershell -ExecutionPolicy Bypass -File deploy\deploy.ps1
#
# PROCEDURE:
#
# 1. IZMENA KODA
#    - Uredi fajlove (api.py, webapp.html, accounts.csv...)
#    - Testiraj lokalno ako je moguće
#
# 2. DEPLOY NA SERVER
#    - Pokreni ovaj skript: powershell -ExecutionPolicy Bypass -File deploy\deploy.ps1
#    - Skript kopira izmenjene fajlove na 192.168.0.247 i restartuje servis
#    - Na kraju ispisuje status servisa — treba da piše "active"
#
# 3. GIT COMMIT I PUSH
#    - git add api.py webapp.html ...       (konkretni fajlovi, NE git add .)
#    - git commit -m "Kratak opis izmene"
#    - git push
#
# NAPOMENA: accounts.csv i .env se NE commituju u git (u .gitignore su).
# =============================================================================

$ErrorActionPreference = "Stop"

$pscp  = "C:\Program Files\PuTTY\pscp.exe"
$plink = "C:\Program Files\PuTTY\plink.exe"

if (-not (Test-Path $pscp) -or -not (Test-Path $plink)) {
    Write-Error "Nije pronađen PuTTY (pscp/plink). Instaliraj sa https://www.putty.org/"
}

# Učitaj kredencijale iz .env (pored ovog skripla)
$envFile = Join-Path $PSScriptRoot ".env"
$cfg = @{}
Get-Content $envFile | Where-Object { $_ -match "=" } | ForEach-Object {
    $k, $v = $_ -split "=", 2
    $cfg[$k.Trim()] = $v.Trim()
}

$ip   = $cfg["SERVER_IP"]
$user = $cfg["SERVER_USER"]
$pass = $cfg["SERVER_PASS"]
$dst  = "${user}@${ip}:/opt/tvi-bee/"

$root = Split-Path -Parent $PSScriptRoot   # direktorijum projekta (bee/)

Write-Host "=== Pčela deploy → $ip ===" -ForegroundColor Cyan

# Fajlovi koji se uvek šalju
$files = @(
    (Join-Path $root "api.py"),
    (Join-Path $root "accounts.csv"),
    (Join-Path $root "webapp.html")
)

foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  → $(Split-Path -Leaf $f)"
        & $pscp -pw $pass $f $dst
    }
}

# APK (ako postoji)
$apk = Join-Path $root "Pcela.apk"
if (Test-Path $apk) {
    Write-Host "  → Pcela.apk"
    & $pscp -pw $pass $apk $dst
}

# Restart servisa
Write-Host ""
Write-Host "Restartujem tvi-bee servis..."
& $plink -pw $pass "${user}@${ip}" "chown -R tvi:tvi /opt/tvi-bee && systemctl restart tvi-bee && sleep 1 && systemctl is-active tvi-bee"

Write-Host ""
Write-Host "=== Gotovo ===" -ForegroundColor Green
