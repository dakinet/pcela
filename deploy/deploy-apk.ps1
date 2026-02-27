# Postavlja Pcela.apk na server (ako fajl postoji).
# Pre toga izgradi APK u Android Studio (BUILD_I_DEPLOY.md u android-app).

$ErrorActionPreference = "Stop"
$beeRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$apkLocal = $null

if (Test-Path (Join-Path $beeRoot "Pcela.apk")) {
    $apkLocal = Join-Path $beeRoot "Pcela.apk"
}
elseif (Test-Path (Join-Path $beeRoot "android-app\app\build\outputs\apk\debug\app-debug.apk")) {
    $apkLocal = Join-Path $beeRoot "android-app\app\build\outputs\apk\debug\app-debug.apk"
}
elseif (Test-Path (Join-Path $beeRoot "android-app\app\build\outputs\apk\release\app-release.apk")) {
    $apkLocal = Join-Path $beeRoot "android-app\app\build\outputs\apk\release\app-release.apk"
}

if (-not $apkLocal) {
    Write-Host "APK nije pronadjen. Izgradi aplikaciju u Android Studio (android-app) pa pokreni ponovo."
    Write-Host "Vidi android-app\BUILD_I_DEPLOY.md"
    exit 1
}

$pscp = "C:\Program Files\PuTTY\pscp.exe"
if (-not (Test-Path $pscp)) {
    Write-Host "Nije pronadjen pscp. Instaliraj PuTTY ili podesi putanju u skripti."
    exit 1
}

Write-Host "Kopiram APK na server: $apkLocal"
& $pscp -pw "neznam123" $apkLocal "root@192.168.0.247:/opt/tvi-bee/Pcela.apk"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Gotovo. Pcela.apk je na serveru; preuzimanje iz weba sada radi."
