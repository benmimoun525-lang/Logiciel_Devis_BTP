@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Restauration de la Version Algerie depuis votre Copie
color 0a

echo ======================================================================
echo   RESTAURATION DE LA VERSION ALGÉRIE DEPUIS VOTRE COPIE
echo   Source : C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html
echo ======================================================================
echo.

if exist "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" (
    echo [*] 1/3 - Sauvegarde de la version Europe dans index_europe.html...
    if exist "index.html" copy /y "index.html" "index_europe.html" >nul

    echo [*] 2/3 - Copie de votre index.html original vers ce dossier...
    copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index.html"

    echo [*] 3/3 - Creation d'une copie de securite permanente index_algerie.html...
    copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index_algerie.html"

    set "TAILLE=0"
    for %%F in ("index.html") do set "TAILLE=%%~zF"

    echo.
    echo ======================================================================
    echo   [SUCCÈS TOTAL] VOTRE LOGICIEL ALGÉRIE EST RESTAURÉ DANS index.html !
    echo ======================================================================
    echo   Taille du fichier copie : !TAILLE! octets
    echo   Emplacement             : %~dp0index.html
    echo ======================================================================
    echo.
    echo Vous pouvez ouvrir index.html ou lancer "lancer.bat" des maintenant !
) else (
    color 0c
    echo [ERREUR] Le fichier "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" est introuvable.
    echo Veuillez verifier que le dossier existe bien.
)

echo.
pause
