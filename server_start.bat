@echo off
chcp 65001 >nul
echo Killing ALL Python processes to ensure clean port usage...
taskkill /F /IM python.exe /T 2>nul

echo Waiting for ports to release...
timeout /t 2 /nobreak >nul

echo Starting SoulMate Web Server...
echo [INFO] Access: http://localhost:8000
python server.py
