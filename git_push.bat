@echo off
setlocal enabledelayedexpansion
title MoggerAI GitHub Auto-Pusher
color 0a

echo ========================================================
echo   🚀 MoggerAI 1-Click Cloud Git Deployment
echo ========================================================
echo.

set "GIT_EXE=%~dp0tools\git\cmd\git.exe"

if not exist "!GIT_EXE!" (
    where git >nul 2>nul
    if !errorlevel! equ 0 (
        set "GIT_EXE=git"
    ) else (
        echo [ERROR] Git executable not found.
        pause
        exit /b 1
    )
)

echo [INFO] Using Git: !GIT_EXE!
echo.

echo [1/4] Initializing Git Repository...
"!GIT_EXE!" init
"!GIT_EXE!" config user.name "Mayank"
"!GIT_EXE!" config user.email "mayankyadav@users.noreply.github.com"

echo [2/4] Staging Cloud Files...
"!GIT_EXE!" add .

echo [3/4] Creating Initial Deployment Commit...
"!GIT_EXE!" commit -m "Deploy MoggerAI 24/7 Cloud Architecture"

echo.
echo ========================================================
set /p REPO_URL="Enter your GitHub Repo URL (e.g. https://github.com/Username/repo.git): "
echo ========================================================

if "%REPO_URL%"=="" (
    echo [ERROR] No URL provided.
    pause
    exit /b 1
)

echo [4/4] Pushing to GitHub (with sync overwrite)...
"!GIT_EXE!" branch -M main
"!GIT_EXE!" remote remove origin >nul 2>nul
"!GIT_EXE!" remote add origin %REPO_URL%
"!GIT_EXE!" push -u origin main --force

echo.
echo ========================================================
echo ✅ Code successfully pushed to GitHub!
echo Now connect this repo to Render.com or Railway.app for 24/7 cloud hosting!
echo ========================================================
pause
