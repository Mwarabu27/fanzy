@echo off
title Fanzy Car Accessories
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Setting up virtual environment for the first time...
    python -m venv venv
    if errorlevel 1 (
        echo Could not create the virtual environment. Is Python installed and on PATH?
        pause
        exit /b 1
    )
    echo Installing dependencies...
    venv\Scripts\python.exe -m pip install --upgrade pip >nul
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo Applying database migrations...
venv\Scripts\python.exe manage.py migrate

echo.
echo Starting Fanzy at http://127.0.0.1:8000/
echo Close this window (or press Ctrl+C) to stop the server.
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/"
venv\Scripts\python.exe manage.py runserver

pause
