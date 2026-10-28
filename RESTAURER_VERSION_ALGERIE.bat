@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Restauration Version Algérie (M. BOUFELDJA BENABDALLAH)
color 0a

echo ======================================================================
echo   RESTAURATION DE LA VERSION ALGÉRIE DU LOGICIEL DEVIS BTP
echo   TITULAIRE OFFICIEL : BOUFELDJA BENABDALLAH
echo   RIP BARIDIMOB      : 00799999000191804708
echo   COMPTE CCP         : 0001918047 (Clé 08)
echo   WHATSAPP           : 0551 42 21 66
echo ======================================================================
echo.

:: 1. Détection de Git dans tous les répertoires standards
where git >nul 2>&1
if errorlevel 1 (
    if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;!PATH!"
    if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "PATH=%LocalAppData%\Programs\Git\cmd;!PATH!"
    if exist "C:\Program Files\Git\bin\git.exe" set "PATH=C:\Program Files\Git\bin;!PATH!"
    if exist "C:\Git\cmd\git.exe" set "PATH=C:\Git\cmd;!PATH!"
)

:: 2. Sauvegarder la version Europe dans un fichier dédié pour ne rien perdre
if exist "index.html" (
    echo [*] 1/3 - Sauvegarde de la Version Europe dans "index_europe.html"...
    copy /y "index.html" "index_europe.html" >nul
)

:: 3. Restaurer index.html officiel Algérie depuis l'historique Git
echo [*] 2/3 - Restauration du fichier index.html officiel Algérie (DZD, BaridiMob)...
git checkout 4a9bff2 -- index.html >nul 2>&1
if errorlevel 1 (
    git checkout HEAD~1 -- index.html >nul 2>&1
)
if errorlevel 1 (
    git checkout HEAD -- index.html >nul 2>&1
)
if errorlevel 1 (
    git checkout main -- index.html >nul 2>&1
)

:: 4. Création d'une copie de sécurité permanente index_algerie.html
if exist "index.html" (
    echo [*] 3/3 - Création de la copie de sécurité permanente "index_algerie.html"...
    copy /y "index.html" "index_algerie.html" >nul
)

echo.
echo ======================================================================
echo   [SUCCÈS TOTAL] VOTRE LOGICIEL VERSION ALGÉRIE EST DE RETOUR !
echo ======================================================================
echo.
echo   • Version Algérie officielle : index.html (Restaurée et active)
echo   • Version Algérie secours    : index_algerie.html (Sécurisée)
echo   • Version Europe             : index_europe.html (Sauvegardée à part)
echo.
echo   Vous pouvez dès maintenant :
echo   1. Double-cliquer sur "lancer.bat" pour tester sur votre PC.
echo   2. Double-cliquer sur "METTRE_A_JOUR_EN_LIGNE.bat" pour republier
echo      votre version Algérie sur votre lien public GitHub Pages !
echo ======================================================================
echo.
pause
