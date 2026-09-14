@echo off
setlocal
set "ROOT=%~dp0.."
set "MENU=%~dp0start_menu.py"

if exist "%ROOT%\.venv\Scripts\python.exe" (
    "%ROOT%\.venv\Scripts\python.exe" "%MENU%" %*
    goto :end
)

if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    "%VIRTUAL_ENV%\Scripts\python.exe" "%MENU%" %*
    goto :end
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%MENU%" %*
    goto :end
)

python "%MENU%" %*

:end
exit /b %errorlevel%
