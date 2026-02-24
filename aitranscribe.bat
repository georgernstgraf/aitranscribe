@echo off
REM aitranscribe Windows wrapper script

SET "DIR=%~dp0"

IF EXIST "%DIR%venv\Scripts\python.exe" (
    "%DIR%venv\Scripts\python.exe" "%DIR%main.py" %*
) ELSE (
    echo Error: Virtual environment not found at %DIR%venv.
    echo Please set it up by running:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    exit /b 1
)
