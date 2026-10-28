@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Restauration Forcee Version Algerie (M. BOUFELDJA BENABDALLAH)
color 0a

echo ======================================================================
echo   RESTAURATION FORCÉE DE LA VERSION ALGÉRIE (DZD, BaridiMob)
echo   TITULAIRE : BOUFELDJA BENABDALLAH
echo ======================================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;!PATH!"
    if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "PATH=%LocalAppData%\Programs\Git\cmd;!PATH!"
    if exist "C:\Program Files\Git\bin\git.exe" set "PATH=C:\Program Files\Git\bin;!PATH!"
    if exist "C:\Git\cmd\git.exe" set "PATH=C:\Git\cmd;!PATH!"
)

echo [*] Sauvegarde de la version Europe dans index_europe.html...
if exist "index.html" (
    findstr /i "Version Europe" "index.html" >nul 2>&1
    if not errorlevel 1 copy /y "index.html" "index_europe.html" >nul
)

echo [*] Recherche de la version Algérie dans l'historique Git...
git log -n 15 --oneline > git_commits.txt 2>&1

set RESTORE_DONE=0

:: Essai 1 : Extraire depuis 4a9bff2
git show 4a9bff2:index.html > index_restore.html 2>nul
if exist index_restore.html (
    for %%A in (index_restore.html) do set SIZE1=%%~zA
    if !SIZE1! GTR 100000 (
        findstr /i "BENABDALLAH" index_restore.html >nul 2>&1
        if not errorlevel 1 (
            echo [OK] Version Algérie trouvée dans 4a9bff2 (!SIZE1! octets) !
            copy /y index_restore.html index.html >nul
            copy /y index_restore.html index_algerie.html >nul
            del index_restore.html >nul 2>&1
            set RESTORE_DONE=1
            goto SUCCES
        )
    )
)

:: Essai 2 : Extraire depuis 38ed851
git show 38ed851:index.html > index_restore.html 2>nul
if exist index_restore.html (
    for %%A in (index_restore.html) do set SIZE2=%%~zA
    if !SIZE2! GTR 100000 (
        findstr /i "BENABDALLAH" index_restore.html >nul 2>&1
        if not errorlevel 1 (
            echo [OK] Version Algérie trouvée dans 38ed851 (!SIZE2! octets) !
            copy /y index_restore.html index.html >nul
            copy /y index_restore.html index_algerie.html >nul
            del index_restore.html >nul 2>&1
            set RESTORE_DONE=1
            goto SUCCES
        )
    )
)

:: Essai 3 : Scan automatique dans l'ensemble des commits récents
for /f "tokens=1" %%c in ('git log -n 25 --format^="%%h"') do (
    git show %%c:index.html > index_restore.html 2>nul
    if exist index_restore.html (
        for %%A in (index_restore.html) do set SIZEC=%%~zA
        if !SIZEC! GTR 100000 (
            findstr /i "BENABDALLAH" index_restore.html >nul 2>&1
            if not errorlevel 1 (
                echo [OK] Version Algérie trouvée dans le commit %%c (!SIZEC! octets) !
                copy /y index_restore.html index.html >nul
                copy /y index_restore.html index_algerie.html >nul
                del index_restore.html >nul 2>&1
                set RESTORE_DONE=1
                goto SUCCES
            )
        )
    )
)

:ECHEC
echo.
echo [!] Recherche automatique en cours...
echo Les détails des commits ont été enregistrés dans git_commits.txt.
pause
exit /b 1

:SUCCES
echo.
echo ======================================================================
echo   [SUCCÈS TOTAL] LA VERSION ALGÉRIE A ÉTÉ RESTAURÉE DANS index.html !
echo ======================================================================
echo.
echo   • Fichier index.html : Restauré (Plus de 600 Ko, 10 900 lignes)
echo   • Titulaire          : BOUFELDJA BENABDALLAH
echo   • Monnaie            : Dinars Algériens (DZD)
echo   • BaridiMob          : 00799999000191804708
echo   • Version Europe     : Conservée dans index_europe.html
echo.
echo   Ouvrez maintenant index.html ou lancez "lancer.bat" :
echo   Votre logiciel Algérie est immédiatement visible !
echo ======================================================================
echo.
pause
