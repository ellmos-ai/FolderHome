@echo off
setlocal
set "ROOT=%~dp0.."
set "MENU=%~dp0start_menu.py"

if exist "%ROOT%\.venv\Scripts\python.exe" (
    "%ROOT%\.venv\Scripts\python.exe" "%MENU%" %*
    exit /b %errorlevel%
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%MENU%" %*
    exit /b %errorlevel%
)

python "%MENU%" %*
exit /b %errorlevel%
