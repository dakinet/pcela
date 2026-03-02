@echo off
REM TVI Bee — deploy fajlova na Linux server
REM Promeniti SERVER_IP pre pokretanja

set SERVER_IP=192.168.0.247
set SERVER_USER=root
set APP_DIR=/opt/tvi-bee

echo === Deploying TVI Bee na %SERVER_IP% ===

REM App fajlovi
scp "%~dp0..\api.py"           %SERVER_USER%@%SERVER_IP%:%APP_DIR%/
scp "%~dp0..\webapp.html"      %SERVER_USER%@%SERVER_IP%:%APP_DIR%/
scp "%~dp0..\ddp_client.py"    %SERVER_USER%@%SERVER_IP%:%APP_DIR%/
scp "%~dp0..\tvi_mcp.py"       %SERVER_USER%@%SERVER_IP%:%APP_DIR%/
scp "%~dp0..\accounts.csv"     %SERVER_USER%@%SERVER_IP%:%APP_DIR%/
scp "%~dp0..\requirements.txt" %SERVER_USER%@%SERVER_IP%:%APP_DIR%/

REM .env (sa kredencijalima)
scp "%~dp0..\.env"             %SERVER_USER%@%SERVER_IP%:%APP_DIR%/

REM Static fajlovi (favicon, logo)
if exist "%~dp0..\static" (
    scp "%~dp0..\static\favicon.ico"          %SERVER_USER%@%SERVER_IP%:%APP_DIR%/static/
    scp "%~dp0..\static\logo.png"             %SERVER_USER%@%SERVER_IP%:%APP_DIR%/static/
    scp "%~dp0..\static\apple-touch-icon.png" %SERVER_USER%@%SERVER_IP%:%APP_DIR%/static/
)

REM SQLite baza projekata (ako postoji)
if exist "%~dp0..\projects\projects.db" (
    scp "%~dp0..\projects\projects.db" %SERVER_USER%@%SERVER_IP%:%APP_DIR%/projects/
)

REM Servis fajl (za setup)
scp "%~dp0tvi-bee.service"     %SERVER_USER%@%SERVER_IP%:/tmp/

REM Napraviti static direktorijum na serveru ako ne postoji, popraviti vlasnistvo, restartovati
ssh %SERVER_USER%@%SERVER_IP% "mkdir -p %APP_DIR%/static && chown -R tvi:tvi %APP_DIR% && systemctl restart tvi-bee"

echo.
echo === Deploy završen ===
echo Provjeri status: ssh %SERVER_USER%@%SERVER_IP% systemctl status tvi-bee
pause
