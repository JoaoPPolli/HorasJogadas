@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
python -m venv .venv_build
if errorlevel 1 goto falha
.venv_build\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto falha
.venv_build\Scripts\python.exe scripts\build_release.py
if errorlevel 1 goto falha
echo Pronto: pacote em release e executavel em dist\HorasJogadas.
echo Preserve toda a pasta do executavel. O instalador usa Inno Setup 6.
pause
exit /b 0
:falha
echo Falha no empacotamento. Leia o erro acima.
pause
exit /b 1
