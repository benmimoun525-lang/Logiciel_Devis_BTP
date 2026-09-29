@echo off
chcp 65001 >nul
title Logiciel Chiffrage Devis BTP - Serveur PC & Smartphone
color 0B

echo =====================================================================
echo          🏗️  LOGICIEL DE CHIFFRAGE DEVIS BTP (ALGERIE)
echo =====================================================================
echo.

:: Detecter l'adresse IP locale du PC pour l'acces sur smartphone
set LOCAL_IP=127.0.0.1
for /f "tokens=4" %%a in ('route print 0.0.0.0 2^>nul ^| find " 0.0.0.0"') do (
    set LOCAL_IP=%%a
    goto :ip_trouvee
)
:ip_trouvee

echo [*] Demarrage du serveur accessible sur PC et Smartphone...
echo.
echo =====================================================================
echo   💻 SUR CE PC :          http://127.0.0.1:8000
echo.
echo   📱 SUR VOTRE SMARTPHONE : (Connecte au meme Wi-Fi que le PC)
echo      Tapez dans Chrome/Safari : http://%LOCAL_IP%:8000
echo =====================================================================
echo.
echo [*] Ouverture de votre navigateur...
start "" "http://127.0.0.1:8000"

:: Demarrer uvicorn sur 0.0.0.0 pour autoriser les connexions depuis le smartphone
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
