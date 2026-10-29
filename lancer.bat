@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Logiciel Chiffrage Devis BTP - Serveur PC & Smartphone
color 0B

echo =====================================================================
echo          🏗️  LOGICIEL DE CHIFFRAGE DEVIS BTP (ALGERIE)
echo =====================================================================
echo.

:: Detection universelle de Git et restauration automatique de la version Algerie si ecrasee
findstr /i "Version Europe" "index.html" >nul 2>&1
if not errorlevel 1 (
    echo [!] Detection de la version Europe dans index.html.
    echo [*] Sauvegarde de la version Europe dans index_europe.html...
    copy /y "index.html" "index_europe.html" >nul
    echo [*] Restauration automatique de votre version Algerie officielle...
    
    set "RESTORED=0"
    if exist "index_algerie.html" (
        for %%F in ("index_algerie.html") do (
            if %%~zF GTR 100000 (
                echo [*] Restauration automatique depuis index_algerie.html...
                copy /y "index_algerie.html" "index.html" >nul
                set "RESTORED=1"
                echo [OK] Version Algerie officielle restauree avec succes !
            )
        )
    )
    if "!RESTORED!"=="0" if exist "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" (
        echo [*] Restauration directe depuis votre dossier de copie de sauvegarde...
        copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index.html" >nul
        copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index_algerie.html" >nul
        echo [OK] Version Algerie officielle restauree avec succes depuis votre copie !
    ) else if "!RESTORED!"=="0" (
        set "GIT_CMD="
        where git >nul 2>&1 && set "GIT_CMD=git"
        if not defined GIT_CMD if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles%\Git\cmd\git.exe"
        if not defined GIT_CMD if exist "%ProgramFiles%\Git\bin\git.exe" set "GIT_CMD=%ProgramFiles%\Git\bin\git.exe"
        if not defined GIT_CMD if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles(x86)%\Git\cmd\git.exe"
        if not defined GIT_CMD if exist "%ProgramFiles(x86)%\Git\bin\git.exe" set "GIT_CMD=%ProgramFiles(x86)%\Git\bin\git.exe"
        if not defined GIT_CMD if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT_CMD=%LocalAppData%\Programs\Git\cmd\git.exe"
        if not defined GIT_CMD if exist "%LocalAppData%\Programs\Git\bin\git.exe" set "GIT_CMD=%LocalAppData%\Programs\Git\bin\git.exe"
        if not defined GIT_CMD if exist "C:\Git\cmd\git.exe" set "GIT_CMD=C:\Git\cmd\git.exe"
        if not defined GIT_CMD if exist "C:\Git\bin\git.exe" set "GIT_CMD=C:\Git\bin\git.exe"
        
        if defined GIT_CMD (
            "!GIT_CMD!" checkout 4a9bff2 -- index.html >nul 2>&1
            if errorlevel 1 "!GIT_CMD!" checkout 38ed851 -- index.html >nul 2>&1
            if errorlevel 1 "!GIT_CMD!" checkout HEAD~1 -- index.html >nul 2>&1
            if errorlevel 1 "!GIT_CMD!" show 4a9bff2:index.html > "index.html" 2>nul
            copy /y "index.html" "index_algerie.html" >nul
            echo [OK] Version Algerie restauree avec succes dans index.html !
        ) else (
            python restaurer_algerie.py >nul 2>&1
        )
    )
    echo.
)

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
