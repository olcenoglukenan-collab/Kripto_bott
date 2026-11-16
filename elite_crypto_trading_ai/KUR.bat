@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ELIT CRYPTO TRADING AI - Kurulum
where py >nul 2>nul || (echo Python bulunamadi. Python 3.12+ kurup PATH'e ekleyin.& pause& exit /b 1)
py -3 -m venv .venv
if errorlevel 1 (echo Sanal ortam olusturulamadi.& pause& exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (echo pip guncellenemedi.& pause& exit /b 1)
pip install -r requirements.txt
if errorlevel 1 (echo Bagimlilik kurulumu basarisiz.& pause& exit /b 1)
if not exist .env copy .env.example .env >nul
echo.
echo Kurulum tamamlandi. BASLAT.bat dosyasini calistirin.
pause
