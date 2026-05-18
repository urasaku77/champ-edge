@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo  ChampEdge セットアップ
echo ========================================
echo.

REM 既にデータがある場合はそのまま起動
if exist "database\battle.db" (
    if exist "recog\setting.json" (
        goto launch
    )
)

echo 旧バージョンのフォルダパスを入力してください。
echo （旧データを引き継がない場合はそのまま Enter）
echo.
set /p OLD_DIR="旧バージョンのフォルダ: "

if "!OLD_DIR!"=="" goto launch
if not exist "!OLD_DIR!\champedge.exe" (
    echo 指定フォルダに champedge.exe が見つかりませんでした。スキップします。
    goto launch
)

echo.
echo データを引き継ぎ中...

for %%F in ("database\battle.db" "recog\setting.json" "recog\capture.json") do (
    if exist "!OLD_DIR!\%%~F" (
        copy /Y "!OLD_DIR!\%%~F" "%%~F" > nul
        echo   %%~F
    )
)

for %%D in ("party\csv" "party\txt" "party\table") do (
    if exist "!OLD_DIR!\%%~D\" (
        xcopy /E /Y /I "!OLD_DIR!\%%~D" "%%~D" > nul
        echo   %%~D
    )
)

echo.
echo 引き継ぎ完了！
echo.

:launch
start "" "%~dp0champedge.exe"
