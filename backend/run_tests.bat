@echo off
rem Run backend tests using repository venv if available, otherwise use system python
setlocal enabledelayedexpansion

rem Resolve script directory
set SCRIPT_DIR=%~dp0

rem Path to repo-level venv
set VENV_ACTIVATE=%SCRIPT_DIR%..\venv\Scripts\activate.bat

if exist "%VENV_ACTIVATE%" (
    echo Activating virtualenv at %SCRIPT_DIR%..\venv
    call "%VENV_ACTIVATE%"
) else (
    echo Virtualenv not found at %SCRIPT_DIR%..\venv
    echo Proceeding with system python (ensure pytest is installed)
)

echo Running pytest...
python -m pytest -q
set EXITCODE=%ERRORLEVEL%
echo pytest exited with %EXITCODE%
exit /b %EXITCODE%





