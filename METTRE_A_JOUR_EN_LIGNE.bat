@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Mise a Jour en Ligne — Logiciel Devis BTP (M. BOUFELDJA BENABDALLAH)
color 0b

echo ======================================================================
echo   PUBLICATION EN LIGNE DU LOGICIEL DEVIS BTP
echo   TITULAIRE OFFICIEL : BOUFELDJA BENABDALLAH
echo   RIP BARIDIMOB      : 00799999000191804708
echo   COMPTE CCP         : 0001918047 (Cle 08)
echo   WHATSAPP           : 0551 42 21 66
echo   Date et Heure      : %DATE% %TIME%
echo ======================================================================
echo.

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

echo [*] 1/4 - Nettoyage et optimisation reseau Git...
echo [*] Nettoyage et optimisation reseau Git... >> "%~dp0deploy_log.txt" 2>&1
git config --global --unset http.proxy >nul 2>&1
git config --global --unset https.proxy >nul 2>&1
git config --system --unset http.proxy >nul 2>&1
git config --system --unset https.proxy >nul 2>&1
git config --unset http.proxy >nul 2>&1
git config --unset https.proxy >nul 2>&1

:: Forcer IPv4 pour empecher les blocages de timeout
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

echo.
echo [*] 2/4 - Indexation des fichiers modifies...
echo [*] Indexation des fichiers... >> "%~dp0deploy_log.txt" 2>&1
git add -A >> "%~dp0deploy_log.txt" 2>&1

echo.
echo [*] 3/4 - Validation de la version (commit)...
echo [*] Validation de la version (commit)... >> "%~dp0deploy_log.txt" 2>&1
git commit -m "Fix : Connexion API universelle GitHub Pages vers Render et configuration multi-domaines" >> "%~dp0deploy_log.txt" 2>&1

:: S'assurer que la branche active s'appelle main
git branch -M main >> "%~dp0deploy_log.txt" 2>&1
git remote set-url origin https://github.com/benmimoun525-lang/Logiciel_Devis_BTP.git >> "%~dp0deploy_log.txt" 2>&1

echo.
echo [*] 4/4 - Envoi en cours vers GitHub et Render (git push)...
echo [*] Envoi vers GitHub et Render (git push)... >> "%~dp0deploy_log.txt" 2>&1

set PUSH_OK=0

:: Tentative 1 : Envoi avec IPv4 forcee
echo [Tentative 1] Synchronisation en cours...
git -c http.ipversion=ipv4 push -u origin main
if !ERRORLEVEL! EQU 0 (
    set PUSH_OK=1
    echo [SUCCES] Push reussi tentative 1 ! >> "%~dp0deploy_log.txt" 2>&1
)

:: Tentative 2 si echec
if !PUSH_OK! EQU 0 (
    echo.
    echo [Tentative 2] Deuxieme essai avec parametres adaptes...
    timeout /t 2 >nul
    git push -4 --set-upstream origin main
    if !ERRORLEVEL! EQU 0 (
        set PUSH_OK=1
        echo [SUCCES] Push reussi tentative 2 ! >> "%~dp0deploy_log.txt" 2>&1
    )
)

:: Tentative 3 si echec
if !PUSH_OK! EQU 0 (
    echo.
    echo [Tentative 3] Troisieme essai standard...
    timeout /t 2 >nul
    git push origin main
    if !ERRORLEVEL! EQU 0 (
        set PUSH_OK=1
        echo [SUCCES] Push reussi tentative 3 ! >> "%~dp0deploy_log.txt" 2>&1
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
if "!PUSH_OK!"=="1" goto SUCCES_AFFICHAGE
goto ECHEC_AFFICHAGE

:SUCCES_AFFICHAGE
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
echo   VOS LIENS OFFICIELS EN LIGNE (24h/24 et 7j/7) :
echo.
echo   [1] LIEN A METTRE SUR VOTRE PUBLICITE CLIENTS (Fonctionne a 100%%) :
echo       https://logiciel-devis-btp.onrender.com
echo.
echo   [2] VOTRE LIEN PERSONNEL TITULAIRE (Tableau de bord complet) :
echo       https://logiciel-devis-btp.onrender.com/?pin=7788#titulaire
echo.
echo   [3] LIEN GITHUB PAGES (Actif des activation dans vos reglages GitHub) :
echo       https://benmimoun525-lang.github.io/Logiciel_Devis_BTP/
echo.
echo   Dans 1 a 2 minutes, ouvrez le lien [1] ou [2] et faites Ctrl + F5 !
echo ======================================================================
goto FIN_AFFICHAGE

:ECHEC_AFFICHAGE
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
echo   SOLUTION IMMEDIATE :
echo   1. Activez le PARTAGE DE CONNEXION 4G sur votre smartphone
echo      (Mobilis, Djezzy ou Ooredoo) et connectez votre PC en Wi-Fi.
echo   2. Relancez "METTRE_A_JOUR_EN_LIGNE.bat".
echo      La synchronisation passera alors sans aucun blocage !
echo.
echo   FONCTIONNEMENT LOCAL 100%% OPERATIONNEL :
echo   Toutes vos modifications sont DEJA actives sur ce PC !
echo   Double-cliquez sur "lancer.bat" et ouvrez :
echo   http://127.0.0.1:8000
echo ======================================================================

:FIN_AFFICHAGE
echo.
echo Le rapport detaille a ete enregistre dans :
echo %CD%\deploy_log.txt
echo.
pause
