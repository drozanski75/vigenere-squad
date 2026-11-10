@echo off
rem Vigenere-Squad : installation automatique sous Windows (Invite de commandes, sans PowerShell).
rem Double-cliquer sur ce fichier, ou le lancer depuis l'Invite de commandes.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Vigenere-Squad - installation
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links;%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Programs\Ollama"

echo ================================================================
echo  Vigenere-Squad : installation
echo  Dossier : %CD%
echo ================================================================

if not exist "pyproject.toml" goto :mauvais_dossier

echo.
echo [1/5] uv (gestionnaire Python)
where uv >nul 2>nul
if %errorlevel%==0 goto :uv_ok
where winget >nul 2>nul
if not %errorlevel%==0 goto :pas_winget
winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
where uv >nul 2>nul
if not %errorlevel%==0 goto :relancer
:uv_ok
echo       uv : OK

echo.
echo [2/5] Ollama (modele de langage local) et Git
where ollama >nul 2>nul
if %errorlevel%==0 goto :ollama_ok
where winget >nul 2>nul
if not %errorlevel%==0 goto :pas_winget
winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
where ollama >nul 2>nul
if not %errorlevel%==0 goto :relancer
:ollama_ok
echo       Ollama : OK
where git >nul 2>nul
if %errorlevel%==0 goto :git_ok
where winget >nul 2>nul
if not %errorlevel%==0 goto :git_ok
echo       Installation de Git (pour la publication sur GitHub)...
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
set "PATH=%PATH%;%ProgramFiles%\Git\cmd"
:git_ok
echo       Git : OK

echo.
echo [3/5] Demarrage du serveur Ollama
call :demarrer_ollama
if not %errorlevel%==0 goto :ollama_ko

echo.
echo [4/5] Donnees, modele principal qwen3:4b et diagnostic complet
echo       (premiere fois : telechargement de Python, des bibliotheques et du modele, 2,5 Go)
uv run vsquad diagnostic --reparer

echo.
echo [5/5] Tous les modeles de l'evaluation (qwen3:4b, qwen3:1.7b, qwen3:0.6b) et epinglage des empreintes
echo       (environ 4 Go au total ; deja installes = instantane)
uv run vsquad modeles
if not %errorlevel%==0 goto :modeles_ko
echo.
echo ================================================================
echo  Installation terminee. Pour utiliser le projet : double-cliquer sur lancer.bat
echo  Ne pas se connecter a ollama.com : le projet n'utilise que des modeles locaux.
echo ================================================================
pause
exit /b 0

:demarrer_ollama
curl -s -o nul http://127.0.0.1:11434/api/version
if %errorlevel%==0 exit /b 0
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
  start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
) else (
  start "Ollama" /min ollama serve
)
echo       attente du serveur Ollama...
for /l %%i in (1,1,30) do (
  timeout /t 2 /nobreak >nul
  curl -s -o nul http://127.0.0.1:11434/api/version && exit /b 0
)
exit /b 1

:mauvais_dossier
echo [ERREUR] pyproject.toml introuvable : ce fichier doit rester dans le dossier du projet.
pause
exit /b 1

:pas_winget
echo [ERREUR] winget est absent. Installer "App Installer" depuis le Microsoft Store,
echo          ou installer uv (https://docs.astral.sh/uv/) et Ollama (https://ollama.com/download) a la main.
pause
exit /b 1

:relancer
echo [INFO] Installation faite. Fermer cette fenetre et relancer installer.bat
echo        (Windows doit recharger le PATH).
pause
exit /b 1

:modeles_ko
echo [ERREUR] Telechargement des modeles interrompu : verifier la connexion et relancer installer.bat
echo          (les telechargements deja faits sont conserves).
pause
exit /b 1

:ollama_ko
echo [ERREUR] Le serveur Ollama ne repond pas. Ouvrir l'application Ollama depuis le menu Demarrer,
echo          attendre son icone dans la barre des taches, puis relancer installer.bat.
pause
exit /b 1
