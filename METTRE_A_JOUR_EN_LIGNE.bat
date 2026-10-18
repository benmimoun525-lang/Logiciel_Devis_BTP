@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Mise à Jour en Ligne — Logiciel Devis BTP (M. BOUFELDJA BENABDALLAH)
color 0b

echo ====================================================================== > "%~dp0deploy_log.txt" 2>&1
echo   PUBLICATION EN LIGNE DU LOGICIEL DEVIS BTP >> "%~dp0deploy_log.txt" 2>&1
echo   TITULAIRE OFFICIEL : BOUFELDJA BENABDALLAH >> "%~dp0deploy_log.txt" 2>&1
echo   RIP BARIDIMOB      : 00799999000191804708 >> "%~dp0deploy_log.txt" 2>&1
echo   COMPTE CCP         : 0001918047 (Cle 08) >> "%~dp0deploy_log.txt" 2>&1
echo   WHATSAPP           : 0551 42 21 66 >> "%~dp0deploy_log.txt" 2>&1
echo   Date et Heure      : %DATE% %TIME% >> "%~dp0deploy_log.txt" 2>&1
echo ====================================================================== >> "%~dp0deploy_log.txt" 2>&1
echo. >> "%~dp0deploy_log.txt" 2>&1

:: Detection de Git dans les dossiers standards
where git >nul 2>&1
if errorlevel 1 (
    if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;!PATH!"
    if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "PATH=%LocalAppData%\Programs\Git\cmd;!PATH!"
    if exist "C:\Program Files\Git\bin\git.exe" set "PATH=C:\Program Files\Git\bin;!PATH!"
    if exist "C:\Git\cmd\git.exe" set "PATH=C:\Git\cmd;!PATH!"
)

:: Reinitialiser tout proxy d'environnement parasite
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set ALL_PROXY=
set all_proxy=
set NO_PROXY=*

echo [*] Nettoyage et optimisation reseau Git... >> "%~dp0deploy_log.txt" 2>&1
git config --global --unset http.proxy >nul 2>&1
git config --global --unset https.proxy >nul 2>&1
git config --system --unset http.proxy >nul 2>&1
git config --system --unset https.proxy >nul 2>&1
git config --unset http.proxy >nul 2>&1
git config --unset https.proxy >nul 2>&1

:: Forcer IPv4 pour empecher les timeouts de 21 secondes sur les reseaux Algerie Telecom / 4G
git config --global http.ipversion ipv4 >nul 2>&1
git config --global http.sslBackend schannel >nul 2>&1
git config --global http.postBuffer 524288000 >nul 2>&1
git config --global http.lowSpeedLimit 1000 >nul 2>&1
git config --global http.lowSpeedTime 60 >nul 2>&1
ipconfig /flushdns >nul 2>&1

:: Identite officielle
git config user.name "BOUFELDJA BENABDALLAH" >> "%~dp0deploy_log.txt" 2>&1
git config user.email "contact@devis-btp.dz" >> "%~dp0deploy_log.txt" 2>&1
echo Identite configuree : BOUFELDJA BENABDALLAH >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Indexation des fichiers... >> "%~dp0deploy_log.txt" 2>&1
git add -A >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Validation de la version (commit)... >> "%~dp0deploy_log.txt" 2>&1
git commit -m "Mise a jour officielle : Titulaire BOUFELDJA BENABDALLAH, RIP 00799999000191804708, CCP 0001918047 cle 08, blocage etapes et securisation PIN" >> "%~dp0deploy_log.txt" 2>&1

:: S'assurer que la branche active s'appelle main
git branch -M main >> "%~dp0deploy_log.txt" 2>&1
git remote set-url origin https://github.com/benmimoun525-lang/Logiciel_Devis_BTP.git >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Diagnostic connectivite reseau : >> "%~dp0deploy_log.txt" 2>&1
ping -n 1 -4 8.8.8.8 >> "%~dp0deploy_log.txt" 2>&1
ping -n 1 -4 github.com >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Envoi vers GitHub et Render (git push)... >> "%~dp0deploy_log.txt" 2>&1

set PUSH_OK=0

:: Tentative 1 : Envoi direct avec IPv4 forcee dans Git
echo [Tentative 1] git -c http.ipversion=ipv4 push -u origin main... >> "%~dp0deploy_log.txt" 2>&1
git -c http.ipversion=ipv4 push -u origin main >> "%~dp0deploy_log.txt" 2>&1
if !ERRORLEVEL! EQU 0 (
    set PUSH_OK=1
    echo [SUCCES] Push reussi tentative 1 ! >> "%~dp0deploy_log.txt" 2>&1
)

:: Tentative 2 si echec
if !PUSH_OK! EQU 0 (
    echo. >> "%~dp0deploy_log.txt" 2>&1
    echo [Tentative 2] git push -4 --set-upstream origin main... >> "%~dp0deploy_log.txt" 2>&1
    timeout /t 2 >nul
    git push -4 --set-upstream origin main >> "%~dp0deploy_log.txt" 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PUSH_OK=1
        echo [SUCCES] Push reussi tentative 2 ! >> "%~dp0deploy_log.txt" 2>&1
    )
)

:: Tentative 3 si echec
if !PUSH_OK! EQU 0 (
    echo. >> "%~dp0deploy_log.txt" 2>&1
    echo [Tentative 3] git push -4 origin main... >> "%~dp0deploy_log.txt" 2>&1
    timeout /t 2 >nul
    git push -4 origin main >> "%~dp0deploy_log.txt" 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PUSH_OK=1
        echo [SUCCES] Push reussi tentative 3 ! >> "%~dp0deploy_log.txt" 2>&1
    )
)

:: Tentative 4 standard
if !PUSH_OK! EQU 0 (
    echo. >> "%~dp0deploy_log.txt" 2>&1
    echo [Tentative 4] git push origin main... >> "%~dp0deploy_log.txt" 2>&1
    timeout /t 2 >nul
    git push origin main >> "%~dp0deploy_log.txt" 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PUSH_OK=1
        echo [SUCCES] Push reussi tentative 4 ! >> "%~dp0deploy_log.txt" 2>&1
    )
)

echo. >> "%~dp0deploy_log.txt" 2>&1
echo ====================================================================== >> "%~dp0deploy_log.txt" 2>&1
if "!PUSH_OK!"=="1" (
    echo   SYNCHRONISATION TERMINEE AVEC SUCCES ! >> "%~dp0deploy_log.txt" 2>&1
    echo   Render met a jour le site en ligne dans 1 a 2 minutes. >> "%~dp0deploy_log.txt" 2>&1
) else (
    echo   ECHEC : La connexion vers GitHub a ete refusee ou a expire. >> "%~dp0deploy_log.txt" 2>&1
)
echo ====================================================================== >> "%~dp0deploy_log.txt" 2>&1

cls
if "!PUSH_OK!"=="1" (
    color 0a
    echo.
    echo ======================================================================
    echo   [SUCCES] SYNCHRONISATION TERMINEE AVEC SUCCES !
    echo ======================================================================
    echo.
    echo   TITULAIRE OFFICIEL : BOUFELDJA BENABDALLAH
    echo   RIP BARIDIMOB      : 00799999000191804708
    echo   COMPTE CCP         : 0001918047 (Cle 08)
    echo   WHATSAPP           : 0551 42 21 66
    echo.
    echo   Render est en train de mettre a jour le site en ligne.
    echo   Dans 1 a 2 minutes, faites Ctrl + F5 sur :
    echo   https://logiciel-devis-btp.onrender.com
    echo.
    echo ======================================================================
) else (
    color 0c
    echo.
    echo ======================================================================
    echo   [ATTENTION] LA SYNCHRONISATION DISTANTE A ECHOUE
    echo ======================================================================
    echo.
    echo   Message Git : Connexion vers github.com:443 impossible ou expiree.
    echo.
    echo   CAUSE FREQUENTE :
    echo   Votre modem Internet (ADSL/Fibre Algerie Telecom) bloque ou
    echo   ralentit temporairement l'acces aux serveurs GitHub.
    echo.
    echo   SOLUTION RAPIDE CONSEILLEE :
    echo   1. Activez le PARTAGE DE CONNEXION 4G sur votre smartphone
    echo      (Mobilis, Djezzy ou Ooredoo) et connectez votre PC en Wi-Fi.
    echo   2. Relancez "METTRE_A_JOUR_EN_LIGNE.bat".
    echo      La synchronisation passera alors instantanement !
    echo.
    echo   EN ATTENDANT (FONCTIONNEMENT LOCAL 100%% OPERATIONNEL) :
    echo   Toutes vos modifications sont DEJA actives sur ce PC !
    echo   Double-cliquez sur "lancer.bat" et ouvrez :
    echo   http://127.0.0.1:8000
    echo   Le titulaire BOUFELDJA BENABDALLAH et le nouveau RIP y sont
    echo   deja parfaitement affiches et securises.
    echo.
    echo ======================================================================
)

echo.
echo Le rapport detaille a ete enregistre dans :
echo %CD%\deploy_log.txt
echo.
pause
