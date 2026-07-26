@echo off
rem Sobe o servidor local e abre o apresentador no Chrome.
rem A webcam nao funciona abrindo o index.html direto (file://), por isso o servidor.

setlocal
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=py"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"

cd /d "%~dp0apresentador"

echo Subindo o servidor em http://localhost:8000 ...
start "Servidor LWL - feche esta janela para encerrar" "%PY%" -m http.server 8000 --bind 127.0.0.1
timeout /t 2 /nobreak >nul

if exist "%CHROME%" (
  start "" "%CHROME%" "http://localhost:8000/index.html"
) else (
  echo Chrome nao encontrado, abrindo no navegador padrao.
  start "" "http://localhost:8000/index.html"
)

echo.
echo O apresentador abriu no navegador.
echo Ao terminar a sessao, baixe os DOIS arquivos: o .webm e o _eventos.csv.
echo Para encerrar, feche a janela "Servidor LWL".
echo.
pause
