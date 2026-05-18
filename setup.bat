@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo  ChampEdge セットアップ
echo ========================================
echo.
echo このファイルがある場所に ChampEdge をインストールします。
echo.
echo すでに別フォルダに旧バージョンがある場合は、
echo そのフォルダパスを入力すると対戦履歴・パーティ等を引き継げます。
echo （引き継がない場合はそのまま Enter を押してください）
echo.
set /p OLD_DIR="旧バージョンのフォルダ（不要なら Enter）: "

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
