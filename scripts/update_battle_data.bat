@echo off
setlocal

set PROJ_ROOT=e:\champ-edge
set PYTHON=%PROJ_ROOT%\.venv\Scripts\python.exe

cd /d "%PROJ_ROOT%"

if not exist "logs" mkdir logs

for /f %%i in ('powershell -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i
set LOG=%PROJ_ROOT%\logs\update_%TODAY%.log

echo [%date% %time%] 開始 >> "%LOG%"
"%PYTHON%" scripts\update_battle_data.py >> "%LOG%" 2>&1
set EXIT=%ERRORLEVEL%
echo [%date% %time%] 終了 exit=%EXIT% >> "%LOG%"

exit /b %EXIT%
