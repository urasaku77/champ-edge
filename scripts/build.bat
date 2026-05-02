@echo off
chcp 65001 > nul
REM このbatはscripts/内に置かれているため、プロジェクトルートへ移動してから実行する
cd /d "%~dp0.."

echo ========================================
echo  ChampEdge ビルド開始
echo ========================================
echo.

.venv\Scripts\pyinstaller champedge.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [エラー] ビルドに失敗しました
    pause
    exit /b 1
)

python scripts\create_update_zip.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [エラー] update zip の作成に失敗しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo  ビルド完了
echo  配布フォルダ: dist\champedge\
echo  配布zip:      dist\champedge_update.zip
echo ========================================
echo.
echo 【配布前の確認事項】
echo  1. dist\champedge\_internal\recog\setting.json の tesseract_path を
echo     利用者の環境に合わせて変更するか、空文字にしてください
echo     （画像認識機能を使わない場合は不要）
echo.
echo 【利用者への案内】
echo  ・champedge.exe をダブルクリックで起動できます
echo  ・画像認識（パーティ自動読み取り）機能を使う場合は
echo    Tesseract OCR のインストールが別途必要です
echo    インストーラ: https://github.com/UB-Mannheim/tesseract/wiki
echo    インストール後、アプリの「モード切替」でパスを設定してください
echo.
pause
