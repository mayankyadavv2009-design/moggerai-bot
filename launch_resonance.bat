@echo off
title RESONANCE APEX - Ultimate Discord Club DJ Bot Launcher
cls
echo =========================================================================
echo                  RESONANCE APEX - DISCORD MUSIC BOT                      
echo =========================================================================
echo.

if not exist .env (
    echo [!] .env file missing! Creating from template...
    copy .env.example .env
)

echo [*] Checking Python dependencies...
python -m pip install -r requirements.txt >nul 2>&1

echo [*] Validating codebase syntax...
python -m py_compile main.py
if %errorlevel% neq 0 (
    echo [X] Syntax error detected! Shutting down...
    pause
    exit /b %errorlevel%
)

echo.
echo [+] Starting RESONANCE APEX Audio Engine & Web Controller...
echo [i] Web Controller: http://localhost:5000
echo.
python main.py
pause
