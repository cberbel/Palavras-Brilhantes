@echo off
rem Arraste a PASTA da sessao para cima deste arquivo, ou execute e digite o caminho.
rem Ele acha sozinho o video, o eventos.csv e a codificacao do olhar, e roda tudo
rem na ordem certa.

setlocal
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=py"

set "ALVO=%~1"
if "%ALVO%"=="" (
  echo Arraste a pasta da sessao para cima deste arquivo, ou digite o caminho abaixo.
  set /p ALVO="Pasta da sessao: "
)

"%PY%" "%~dp0analisador\processar.py" "%ALVO%"
echo.
pause
