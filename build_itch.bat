@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==================================================
echo   Gerando o pacote para o itch.io
echo   (leva alguns minutos e precisa de internet)
echo ==================================================
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em python.org e marque "Add Python to PATH".
  pause
  exit /b 1
)
python empacotar_release.py %*
if errorlevel 1 (
  echo.
  echo *** FALHOU - leia a mensagem acima. NAO publique nada. ***
  pause
  exit /b 1
)
echo.
echo Abra a pasta "release" para ver o resultado.
pause
