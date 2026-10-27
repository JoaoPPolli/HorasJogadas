@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo HorasJogadas - NOVA INTERFACE PARA REVISAO
echo Esta versao usa uma COPIA dos dados. O app atual continua separado.
echo Feche o app atual antes da primeira copia para incluir os dados mais recentes.
echo As partidas registradas na revisao NAO voltam automaticamente para o app atual.
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.10 a 3.13 com Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv_qt\Scripts\python.exe (
  python -m venv .venv_qt
  if errorlevel 1 goto falha
)
.venv_qt\Scripts\python.exe -c "import PySide6,certifi; assert PySide6.__version__ == '6.8.3' and certifi.__version__ == '2026.10.23'" >nul 2>nul
if errorlevel 1 (
  .venv_qt\Scripts\python.exe -m pip install -r requirements-qt.txt
  if errorlevel 1 goto falha
)
.venv_qt\Scripts\python.exe app_qt.py --review %*
if errorlevel 1 goto falha
exit /b 0
:falha
echo Nao foi possivel iniciar. Leia o erro acima; os dados originais nao foram alterados pela revisao.
pause
exit /b 1
