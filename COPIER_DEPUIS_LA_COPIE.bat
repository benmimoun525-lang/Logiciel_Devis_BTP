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

if exist "index_europe.html" (
    echo [*] 1/2 - Copie de index_europe.html (Version Algérie 100%% Autonome) vers index.html...
    copy /y "index_europe.html" "index.html" >nul

    echo [*] 2/2 - Creation d'une copie de securite permanente index_algerie.html...
    copy /y "index_europe.html" "index_algerie.html" >nul

    set "TAILLE=0"
    for %%F in ("index.html") do set "TAILLE=%%~zF"

    echo.
    echo ======================================================================
    echo   [SUCCÈS TOTAL] VOTRE LOGICIEL ALGÉRIE EST ACTIF DANS index.html !
    echo ======================================================================
    echo   Taille du fichier copie : !TAILLE! octets (Mode 100%% Autonome Zero-Serveur)
    echo   Emplacement             : %~dp0index.html
    echo ======================================================================
    echo.
    echo Vous pouvez ouvrir index.html ou lancer "lancer.bat" des maintenant !
) else if exist "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" (
    echo [*] Copie depuis C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html...
    copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index.html"
    copy /y "C:\Users\hp\Logiciel_Devis_BTP_COPIE\index.html" "index_algerie.html"
    echo [OK] Copie effectuee !
) else (
    color 0c
    echo [ERREUR] Aucun fichier source trouve.
)

echo.
pause
