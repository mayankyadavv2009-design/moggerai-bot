#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 Starting MoggerAI Cloud Deployment (Bot + 24/7 Trainer)"
echo "=========================================================="

# 1. Launch the 24/7 Continuous Training Suite in Background
echo "[INFO] Launching Background Autonomous Neural Trainer..."
python -u scripts/continuous_trainer.py &

# 2. Launch the Main Discord Bot & Web Dashboard in Foreground
echo "[INFO] Starting MoggerAI Discord Bot & Web Server..."
exec python -u main.py
