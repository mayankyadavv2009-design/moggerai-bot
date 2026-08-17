@echo off
title MoggerAI 24/7 Continuous Training & Auto-Learning Daemon
color 0b
echo ========================================================
echo   MoggerAI 24/7 Autonomous Neural Training Daemon
echo ========================================================
echo [INFO] Training Engine: Groq Ultra-Fast API + Gemini Failover
echo [INFO] Auto-Distillation & Discord Learning: Active
echo [INFO] Status Dashboard: http://localhost:5000/training
echo ========================================================

:LOOP
echo [%date% %time%] Launching Continuous Training Cycle...
python -u "%~dp0scripts\continuous_trainer.py"
echo [%date% %time%] Process exited or network hiccup. Auto-restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto LOOP
