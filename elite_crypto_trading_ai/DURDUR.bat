@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo stop > STOP_WORKER
echo Worker guvenli sekilde durdurulacak. Dashboard terminalinde Ctrl+C yapabilirsiniz.
pause
