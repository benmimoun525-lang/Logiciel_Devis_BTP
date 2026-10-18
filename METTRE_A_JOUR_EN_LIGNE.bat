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

echo [*] Repertoire de travail : %CD% >> "%~dp0deploy_log.txt" 2>&1

:: Detection de Git dans les chemins standards
where git >nul 2>&1
if errorlevel 1 (
    if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;!PATH!"
    if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "PATH=%LocalAppData%\Programs\Git\cmd;!PATH!"
    if exist "C:\Program Files\Git\bin\git.exe" set "PATH=C:\Program Files\Git\bin;!PATH!"
    if exist "C:\Git\cmd\git.exe" set "PATH=C:\Git\cmd;!PATH!"
)

where git >> "%~dp0deploy_log.txt" 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe ou introuvable dans le PATH. >> "%~dp0deploy_log.txt" 2>&1
    type "%~dp0deploy_log.txt"
    echo.
    echo Veuillez installer Git depuis https://git-scm.com/download/win
    pause
    exit /b 1
)

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Version de Git detectee : >> "%~dp0deploy_log.txt" 2>&1
git --version >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Configuration des identifiants Git : >> "%~dp0deploy_log.txt" 2>&1
git config user.name "BOUFELDJA BENABDALLAH" >> "%~dp0deploy_log.txt" 2>&1
git config user.email "contact@devis-btp.dz" >> "%~dp0deploy_log.txt" 2>&1
echo Nom configure : BOUFELDJA BENABDALLAH >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Statut du depot Git avant synchronisation : >> "%~dp0deploy_log.txt" 2>&1
git status >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Serveurs distants configures (git remote -v) : >> "%~dp0deploy_log.txt" 2>&1
git remote -v >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Liste des branches (git branch -a) : >> "%~dp0deploy_log.txt" 2>&1
git branch -a >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Indexation des fichiers modifies (git add -A) : >> "%~dp0deploy_log.txt" 2>&1
git add -A >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Enregistrement de la version (git commit) : >> "%~dp0deploy_log.txt" 2>&1
git commit -m "Mise a jour officielle : Titulaire BOUFELDJA BENABDALLAH, RIP 00799999000191804708, CCP 0001918047 cle 08, blocage etapes et securisation PIN" >> "%~dp0deploy_log.txt" 2>&1

echo. >> "%~dp0deploy_log.txt" 2>&1
echo [*] Envoi vers GitHub et Render (git push) : >> "%~dp0deploy_log.txt" 2>&1

set PUSH_OK=0

git push origin main >> "%~dp0deploy_log.txt" 2>&1
if !ERRORLEVEL! EQU 0 (
    set PUSH_OK=1
    echo [SUCCES] Push reussi sur origin main ! >> "%~dp0deploy_log.txt" 2>&1
) else (
    echo [Info] Tentative sur origin master... >> "%~dp0deploy_log.txt" 2>&1
    git push origin master >> "%~dp0deploy_log.txt" 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PUSH_OK=1
        echo [SUCCES] Push reussi sur origin master ! >> "%~dp0deploy_log.txt" 2>&1
    ) else (
        echo [Info] Tentative de git push direct... >> "%~dp0deploy_log.txt" 2>&1
        git push >> "%~dp0deploy_log.txt" 2>&1
        if !ERRORLEVEL! EQU 0 (
            set PUSH_OK=1
            echo [SUCCES] Push direct reussi ! >> "%~dp0deploy_log.txt" 2>&1
        )
    )
)

echo. >> "%~dp0deploy_log.txt" 2>&1
echo ====================================================================== >> "%~dp0deploy_log.txt" 2>&1
if "!PUSH_OK!"=="1" (
    echo   SUCCES TOTAL : SYNCHRONISATION EN LIGNE REUSSIE ! >> "%~dp0deploy_log.txt" 2>&1
    echo   Render met a jour le site en 1 a 2 minutes. >> "%~dp0deploy_log.txt" 2>&1
) else (
    echo   ATTENTION : Le push distant n'a pas pu aboutir automatiquement. >> "%~dp0deploy_log.txt" 2>&1
    echo   Consultez le detail ci-dessus pour voir le message de Git. >> "%~dp0deploy_log.txt" 2>&1
)
echo ====================================================================== >> "%~dp0deploy_log.txt" 2>&1

:: Affichage de l'integralite du journal a l'ecran
type "%~dp0deploy_log.txt"

echo.
echo ======================================================================
echo   Le rapport complet a ete enregistre dans le fichier :
echo   %CD%\deploy_log.txt
echo ======================================================================
echo.
pause
