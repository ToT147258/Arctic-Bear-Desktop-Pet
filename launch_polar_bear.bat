@echo off
setlocal

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

set "PYTHON_EXE="
if exist "%APP_DIR%.venv\Scripts\pythonw.exe" set "PYTHON_EXE=%APP_DIR%.venv\Scripts\pythonw.exe"
if not defined PYTHON_EXE if exist "%APP_DIR%.local_deps\Scripts\pythonw.exe" set "PYTHON_EXE=%APP_DIR%.local_deps\Scripts\pythonw.exe"
if not defined PYTHON_EXE (
    for %%P in (pythonw.exe pyw.exe python.exe py.exe) do (
        where %%P >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=%%P"
            goto :found_python
        )
    )
)

:found_python
if not defined PYTHON_EXE (
    msg * "Python was not found. Please install Python 3.10+ and run: pip install -r requirements.txt"
    exit /b 1
)

if /i "%PYTHON_EXE%"=="py.exe" (
    start "PolarBear" py -3 "%APP_DIR%main.py"
) else if /i "%PYTHON_EXE%"=="pyw.exe" (
    start "PolarBear" pyw -3 "%APP_DIR%main.py"
) else (
    start "PolarBear" "%PYTHON_EXE%" "%APP_DIR%main.py"
)

exit /b 0
