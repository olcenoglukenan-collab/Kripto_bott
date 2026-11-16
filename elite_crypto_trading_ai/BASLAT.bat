@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Once KUR.bat dosyasini calistirin.& pause& exit /b 1)
if exist STOP_WORKER del STOP_WORKER
start "ELIT Crypto Worker" /min "%~dp0.venv\Scripts\python.exe" "%~dp0worker.py"
call .venv\Scripts\activate.bat
streamlit run app.py
pause
