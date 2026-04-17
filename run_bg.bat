@echo off
REM SoulMate Background Controller Runner
cd %~dp0
call .venv\Scripts\activate
python main.py
