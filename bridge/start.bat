@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Omni-Ext Bridge
cd /d "%~dp0"
if not exist "%~dp0logs" mkdir "%~dp0logs" >nul 2>nul
set "LF=%~dp0logs\start.log"
echo ==== %DATE% %TIME% start ====>>"%LF%" 2>nul
echo.
echo   === Omni-Ext Bridge ===
echo.
echo [1/3] Looking for Python...
set "PY="
where py >nul 2>nul && set "PY=py -3"
call :vpy && goto :found
set "PY=python"
call :vpy && goto :found
for %%R in ("%LOCALAPPDATA%\Programs\Python" "%ProgramFiles%" "%ProgramFiles(x86)%") do (
 if exist "%%~R" for /f "delims=" %%D in ('dir /b /ad /o-n "%%~R\Python3*" 2^>nul') do (
  if exist "%%~R\%%D\python.exe" set "PY="%%~R\%%D\python.exe"" && call :vpy && goto :found
 ))
set "PY="
echo Python not found. Installing via winget...
winget install --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements >nul 2>nul
set "PY=py -3"
call :vpy && goto :found
set "PY=python"
call :vpy && goto :found
echo Install Python from https://www.python.org/ then run again.
pause
exit /b 1
:found
echo        Found: %PY%
echo [2/3] Checking websockets...
%PY% -c "import websockets" >nul 2>nul
if errorlevel 1 (
 echo Installing websockets...
 %PY% -m pip install --user websockets >nul 2>nul
 if errorlevel 1 echo pip failed; pause; exit /b 1)
echo        OK
echo [3/3] Starting bridge...
set "OPID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :17613 ^| findstr LISTENING 2^>nul') do set "OPID=%%a"
if defined OPID (
 echo Previous bridge (pid !OPID!) running, replacing...
 taskkill /F /T /PID !OPID! >nul 2>nul
 timeout /t 1 /nobreak >nul)
echo.
echo  Keep this window open - closing it stops the bridge.
echo.
%PY% "%~dp0bridge.py"
echo Bridge stopped.
pause >nul
exit /b 0
:vpy
%PY% -m pip --version >nul 2>nul || exit /b 1
%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
exit /b %errorlevel%
