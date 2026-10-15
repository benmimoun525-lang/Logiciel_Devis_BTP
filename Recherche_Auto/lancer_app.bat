@echo off
chcp 65001 >nul
title AutoCote - Recherche & Cote de Vehicules d'Occasion
color 0B

echo ======================================================================
echo    🚗 AutoCote - Recherche & Cote de Véhicules d'Occasion
echo ======================================================================
echo.

cd /d "%~dp0"

:: Recherche du chemin de Python
set "PYTHON_EXE="

if exist "%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe"
) else if exist "%USERPROFILE%\AppData\Local\Python\bin\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Python\bin\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: Détection IP locale pour accès PC & Smartphone
set LOCAL_IP=127.0.0.1
for /f "tokens=4" %%a in ('route print 0.0.0.0 2^>nul ^| find " 0.0.0.0"') do (
    set LOCAL_IP=%%a
    goto :ip_trouvee
)
:ip_trouvee

echo [*] Python détecté : %PYTHON_EXE%
echo [*] Démarrage du serveur...
echo.
echo ======================================================================
echo   💻 SUR CE PC :          http://127.0.0.1:8050
echo.
echo   📱 SUR SMARTPHONE :     http://%LOCAL_IP%:8050
echo      (Connecté au même réseau Wi-Fi)
echo ======================================================================
echo.
echo [*] Ouverture de votre navigateur...
start "" "http://127.0.0.1:8050"

"%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8050 --reload

echo.
echo Serveur arrêté.
pause
