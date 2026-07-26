@echo off
rem Abre o codificador manual de olhar. Nao precisa de servidor: ele le o video
rem direto do disco.

setlocal
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"

if exist "%CHROME%" (
  start "" "%CHROME%" "file:///%~dp0codificador/index.html"
) else (
  start "" "%~dp0codificador\index.html"
)
