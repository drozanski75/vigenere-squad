@echo off
rem Vigenere-Squad : menu de lancement (double-cliquer).
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Vigenere-Squad
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links;%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Programs\Ollama"
where uv >nul 2>nul
if not %errorlevel%==0 (
  echo uv est absent : lancer d'abord installer.bat
  pause
  exit /b 1
)

:menu
echo.
echo ================================================================
echo  Vigenere-Squad - le modele decide et explique, le code calcule
echo ================================================================
echo   1. Diagnostic de l'installation
echo   2. Casser exemple_chiffre.txt avec les agents
echo   3. Casser mon propre texte chiffre
echo   4. Casser sans IA, reference rapide
echo   5. Interface graphique dans le navigateur
echo   6. Rejouer un chiffre du corpus et voir les traces
echo   7. Evaluation reduite, 15 a 30 min
echo   8. Evaluation complete, longue, reprenable
echo   0. Quitter
echo.
set "choix="
set /p "choix=Votre choix : "
if "%choix%"=="1" goto :diag
if "%choix%"=="2" goto :exemple
if "%choix%"=="3" goto :texte
if "%choix%"=="4" goto :sans_ia
if "%choix%"=="5" goto :demo
if "%choix%"=="6" goto :rejouer
if "%choix%"=="7" goto :petite
if "%choix%"=="8" goto :complete
if "%choix%"=="0" exit /b 0
goto :menu

:diag
call :ollama
uv run vsquad diagnostic
goto :pause

:exemple
call :ollama || goto :pause
uv run vsquad casser --fichier exemple_chiffre.txt --expliquer
goto :pause

:texte
call :ollama || goto :pause
echo Collez le texte chiffre sur une seule ligne, puis Entree :
set "texte="
set /p "texte=> "
if not defined texte goto :menu
> "%TEMP%\vsquad_chiffre.txt" echo(%texte%
uv run vsquad casser --fichier "%TEMP%\vsquad_chiffre.txt" --expliquer
goto :pause

:sans_ia
set "fichier=exemple_chiffre.txt"
set /p "fichier=Fichier a casser [exemple_chiffre.txt] : "
uv run vsquad casser --fichier "%fichier%" --llm aucun
goto :pause

:demo
call :ollama || goto :pause
echo L'interface s'ouvre sur http://127.0.0.1:7860 ; fermer cette fenetre pour l'arreter.
start "" http://127.0.0.1:7860
uv run --extra demo python -m vigenere_squad.demo
goto :pause

:rejouer
call :ollama || goto :pause
set "id=standard-vigenere-0600-0"
set /p "id=Identifiant [standard-vigenere-0600-0] : "
uv run vsquad rejouer --id "%id%" --config b_qwen3_4b --expliquer
goto :pause

:petite
call :ollama || goto :pause
uv run vsquad reproduire --petit
goto :pause

:complete
call :ollama || goto :pause
echo Duree : plusieurs heures. Interrompre avec Ctrl+C ; relancer reprend la ou ca s'est arrete.
echo Le PC ne se mettra pas en veille pendant le calcul (l'ecran peut s'eteindre).
uv run vsquad modeles
if not %errorlevel%==0 goto :pause
uv run vsquad environnement
uv run vsquad evaluer
uv run vsquad metriques
uv run vsquad site
goto :pause

:pause
echo.
pause
goto :menu

:ollama
curl -s -o nul http://127.0.0.1:11434/api/version
if %errorlevel%==0 exit /b 0
echo Demarrage d'Ollama...
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
  start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
) else (
  start "Ollama" /min ollama serve
)
for /l %%i in (1,1,30) do (
  timeout /t 2 /nobreak >nul
  curl -s -o nul http://127.0.0.1:11434/api/version && exit /b 0
)
echo [ERREUR] Ollama ne repond pas : ouvrir l'application Ollama depuis le menu Demarrer.
exit /b 1
