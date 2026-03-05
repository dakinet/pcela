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

$root = Split-Path -Parent $PSScriptRoot   # direktorijum projekta (bee/)

Write-Host "=== Pčela deploy → $ip ===" -ForegroundColor Cyan

# Funkcija za kopiranje jednog fajla sa verifikacijom
function Copy-ToServer($localPath, $remoteDir) {
    $name = Split-Path -Leaf $localPath
    $localSize = (Get-Item $localPath).Length
    Write-Host "  → $name  ($localSize B lokalno)" -NoNewline

    # Kopiraj fajl (-batch: bez interaktivnih pitanja, failuje ako host key nije poznat)
    & $pscp -batch -pw $pass $localPath "${user}@${ip}:${remoteDir}"
    if ($LASTEXITCODE -ne 0) {
        Write-Host " [GREŠKA pscp exit=$LASTEXITCODE]" -ForegroundColor Red
        throw "pscp failed za $name (exit code $LASTEXITCODE)"
    }

    # Verifikacija: provjeri veličinu na serveru
    $remoteSize = & $plink -batch -pw $pass "${user}@${ip}" "stat -c%s ${remoteDir}${name} 2>/dev/null || echo 0"
    $remoteSize = $remoteSize.Trim()
    # Linux fajl je manji zbog LF umjesto CRLF — dozvoli razliku do 5%
    $ratio = if ([int]$remoteSize -gt 0) { [int]$remoteSize / $localSize } else { 0 }
    if ($ratio -lt 0.90) {
        Write-Host " [GREŠKA: server=$remoteSize B, lokalno=$localSize B]" -ForegroundColor Red
        throw "Verifikacija neuspješna za $name"
    }

    Write-Host "  OK server=$remoteSize B" -ForegroundColor Green
}

# Fajlovi koji se uvek šalju
$files = @(
    (Join-Path $root "api.py"),
    (Join-Path $root "accounts.csv"),
    (Join-Path $root "webapp.html")
)

foreach ($f in $files) {
    if (Test-Path $f) {
        Copy-ToServer $f "/opt/tvi-bee/"
    }
}

# APK (ako postoji)
$apk = Join-Path $root "Pcela.apk"
if (Test-Path $apk) {
    Write-Host "  → Pcela.apk" -NoNewline
    & $pscp -batch -pw $pass $apk "${user}@${ip}:/opt/tvi-bee/"
    if ($LASTEXITCODE -ne 0) { throw "pscp failed za Pcela.apk" }
    Write-Host "  OK" -ForegroundColor Green
}

# Restart servisa
Write-Host ""
Write-Host "Restartujem tvi-bee servis..."
& $plink -batch -pw $pass "${user}@${ip}" "chown -R tvi:tvi /opt/tvi-bee && systemctl restart tvi-bee && sleep 1 && systemctl is-active tvi-bee"
if ($LASTEXITCODE -ne 0) {
    Write-Host "UPOZORENJE: restart možda nije uspio (exit=$LASTEXITCODE)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Gotovo ===" -ForegroundColor Green
