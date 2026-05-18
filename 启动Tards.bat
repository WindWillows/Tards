@echo off
chcp 65001 >/dev/null
cd /d "%~dp0"
.venv\Scripts\python.exe Gamestart.py
pause
