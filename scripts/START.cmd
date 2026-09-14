@echo off
setlocal
set "ROOT=%~dp0.."
set "MENU=%~dp0start_menu.py"
set "CONFIG_ARGS="

rem Source-checkout convenience: use the sibling installed configuration only
rem when both trusted starter wrappers and launch.json are present. An explicit
rem --config-dir argument or FOLDERHOME_CONFIG_DIR still wins.
if not defined FOLDERHOME_CONFIG_DIR (
    for %%I in ("%ROOT%\..\..\folderhome-config") do set "LOCAL_CONFIG=%%~fI"
)
if not defined FOLDERHOME_CONFIG_DIR if exist "%LOCAL_CONFIG%\START-APP.cmd" if exist "%LOCAL_CONFIG%\START-SETUP.cmd" if exist "%LOCAL_CONFIG%\launch.json" (
    set "CONFIG_ARGS=--config-dir "%LOCAL_CONFIG%""
)

if exist "%ROOT%\.venv\Scripts\python.exe" (
    "%ROOT%\.venv\Scripts\python.exe" "%MENU%" %CONFIG_ARGS% %*
    goto :end
)

if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    "%VIRTUAL_ENV%\Scripts\python.exe" "%MENU%" %CONFIG_ARGS% %*
    goto :end
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -3 "%MENU%" %CONFIG_ARGS% %*
        goto :end
    )
)

python "%MENU%" %CONFIG_ARGS% %*

:end
exit /b %errorlevel%
