@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Para executar o codigo, instale Python 3.10 a 3.13 com Add Python to PATH.
  echo Sem Python: https://joaoppolli.github.io/HorasJogadas/
  pause
  exit /b 1
)
if not exist .venv_qt\Scripts\python.exe (
  python -m venv .venv_qt
  if errorlevel 1 goto falha
)
.venv_qt\Scripts\python.exe -c "import PySide6; assert PySide6.__version__ == '6.8.3'" >nul 2>nul
if errorlevel 1 (
  .venv_qt\Scripts\python.exe -m pip install -r requirements-qt.txt
  if errorlevel 1 goto falha
)
.venv_qt\Scripts\python.exe app_qt.py %*
if errorlevel 1 goto falha
exit /b 0
:falha
echo Nao foi possivel iniciar. Leia o erro acima.
pause
exit /b 1
