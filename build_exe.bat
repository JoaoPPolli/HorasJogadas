@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==================================================
echo   Criando o HorasJogadas.exe  (so precisa fazer 1 vez)
echo ==================================================
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em python.org e marque "Add Python to PATH".
  pause
  exit /b 1
)
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo Falha ao instalar o PyInstaller.
  pause
  exit /b 1
)
set ICONE=
if exist icon.ico set ICONE=--icon icon.ico
python -m PyInstaller --noconfirm --clean --onefile --windowed --name HorasJogadas %ICONE% app.py
if errorlevel 1 (
  echo Falha ao gerar o exe.
  pause
  exit /b 1
)
copy /Y dist\HorasJogadas.exe HorasJogadas.exe >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q HorasJogadas.spec 2>nul
echo.
echo Pronto! Abra o HorasJogadas.exe que esta nesta pasta.
echo Daqui em diante, atualize pelo app: Configuracoes ^> Atualizar app...
pause
