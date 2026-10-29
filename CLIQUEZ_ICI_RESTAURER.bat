@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Restauration Version Algerie (M. BOUFELDJA BENABDALLAH)
color 0a

echo ======================================================================
echo   RESTAURATION FORCÉE DE LA VERSION ALGÉRIE (OFFICIELLE)
echo   TITULAIRE : BOUFELDJA BENABDALLAH
echo   BARIDIMOB : 00799999000191804708
echo   COMPTE CCP: 0001918047 (Cle 08)
echo   WHATSAPP  : 0551 42 21 66
echo ======================================================================
echo.

:: 1. Détection universelle de Git
set "GIT_CMD="
where git >nul 2>&1
if not errorlevel 1 set "GIT_CMD=git"

if not defined GIT_CMD (
    if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles%\Git\cmd\git.exe"
    if exist "%ProgramFiles%\Git\bin\git.exe" set "GIT_CMD=%ProgramFiles%\Git\bin\git.exe"
    if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT_CMD=%ProgramFiles(x86)%\Git\cmd\git.exe"
    if exist "%ProgramFiles(x86)%\Git\bin\git.exe" set "GIT_CMD=%ProgramFiles(x86)%\Git\bin\git.exe"
    if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT_CMD=%LocalAppData%\Programs\Git\cmd\git.exe"
    if exist "%LocalAppData%\Programs\Git\bin\git.exe" set "GIT_CMD=%LocalAppData%\Programs\Git\bin\git.exe"
    if exist "C:\Git\cmd\git.exe" set "GIT_CMD=C:\Git\cmd\git.exe"
    if exist "C:\Git\bin\git.exe" set "GIT_CMD=C:\Git\bin\git.exe"
)

if not defined GIT_CMD (
    color 0c
    echo [ERREUR] Git n'a pas été trouvé dans les dossiers standards.
    echo.
    pause
    exit /b 1
)

echo [*] Git détecté avec succès.
echo.

:: 2. Sauvegarde de la version Europe dans index_europe.html
if exist "index.html" (
    findstr /i "Version Europe" "index.html" >nul 2>&1
    if not errorlevel 1 (
        echo [*] Sauvegarde de la version Europe dans "index_europe.html"...
        copy /y "index.html" "index_europe.html" >nul
    )
)

:: 3. Restauration directe de index.html
set "DEJA_ALGERIE=0"
if exist "index.html" (
    findstr /i "Devis BTP Algérie" "index.html" >nul 2>&1
    if not errorlevel 1 (
        for %%F in ("index.html") do (
            if %%~zF GTR 100000 set "DEJA_ALGERIE=1"
        )
    )
)

if "!DEJA_ALGERIE!"=="1" (
    echo [OK] La version Algérie officielle 100%% autonome est déjà active dans index.html.
    copy /y "index.html" "index_algerie.html" >nul
) else if exist "index_algerie.html" (
    set "TAILLE_ALG=0"
    for %%F in ("index_algerie.html") do set "TAILLE_ALG=%%~zF"
    if !TAILLE_ALG! GTR 100000 (
        echo [*] Restauration depuis votre copie locale index_algerie.html...
        copy /y "index_algerie.html" "index.html" >nul
    ) else if exist "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" (
        echo [*] Restauration de secours depuis C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html...
        copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index.html" >nul
        copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index_algerie.html" >nul
    )
) else if exist "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" (
    echo [*] Restauration de secours depuis C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html...
    copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index.html" >nul
    copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index_algerie.html" >nul
) else (
    echo [*] Restauration du fichier source original index.html depuis Git...
    "!GIT_CMD!" checkout 4a9bff2 -- index.html >nul 2>&1
    if errorlevel 1 "!GIT_CMD!" checkout 38ed851 -- index.html >nul 2>&1
    if errorlevel 1 "!GIT_CMD!" checkout HEAD~1 -- index.html >nul 2>&1
    if errorlevel 1 (
        echo [*] Extraction directe par flux Git...
        "!GIT_CMD!" show 4a9bff2:index.html > "index.html" 2>nul
        if errorlevel 1 "!GIT_CMD!" show 38ed851:index.html > "index.html" 2>nul
    )
)

:: 4. Vérification et validation
set "TAILLE=0"
if exist "index.html" for %%F in ("index.html") do set "TAILLE=%%~zF"

if !TAILLE! GTR 100000 (
    copy /y "index.html" "index_algerie.html" >nul
    echo.
    echo ======================================================================
    echo   [SUCCÈS TOTAL] VOTRE LOGICIEL ALGÉRIE EST RESTAURÉ DANS index.html !
    echo ======================================================================
    echo   Taille du fichier  : !TAILLE! octets (environ 10 900 lignes)
    echo   Titulaire officiel : BOUFELDJA BENABDALLAH
    echo   BaridiMob          : 00799999000191804708
    echo   CCP                : 0001918047 (Cle 08)
    echo   Devise             : Dinars Algériens (DZD)
    echo.
    echo   Fichiers opérationnels :
    echo     ✅ index.html         - Votre version Algérie officielle
    echo     ✅ index_algerie.html - Copie de sécurité permanente
    echo     ✅ index_europe.html  - Version Europe (préservée)
    echo ======================================================================
    echo.
    echo Vous pouvez ouvrir votre navigateur ou lancer "lancer.bat" dès maintenant.
) else (
    color 0c
    echo.
    echo ======================================================================
    echo   [ATTENTION] La taille du fichier est anormale (!TAILLE! octets).
    echo ======================================================================
)

echo.
pause
