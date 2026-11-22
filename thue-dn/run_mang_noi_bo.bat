@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Dang cai dat lan dau, vui long cho...
  python -m venv .venv || (echo Chua cai Python. Tai tai python.org va tick "Add Python to PATH". & pause & exit /b 1)
  .venv\Scripts\pip install -r requirements.txt
)
echo.
echo MAY CHINH - cho may khac cung mang truy cap. Neu Windows hoi tuong lua, chon "Private networks" roi Allow.
echo.
start "" http://127.0.0.1:5000
.venv\Scripts\python app.py --mang-noi-bo
pause
