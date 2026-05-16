# -*- mode: python ; coding: utf-8 -*-
import glob as _glob
import os
import subprocess as _sp
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ttkthemes のテーマファイル（.tcl / 画像）を取得
ttkthemes_datas = collect_data_files('ttkthemes')

# Windows のみ favicon.ico を適用（macOS は ICNS が必要なので未指定）
_icon = 'image/favicon.ico' if sys.platform == 'win32' else None

# Tesseract バイナリをバンドル（コンパイル版で OCR フォールバックが動作するように）
_tess_datas = []
if sys.platform == 'win32':
    import json as _json
    _tess_dir = r'C:\Program Files\Tesseract-OCR'
    try:
        with open('recog/setting.json') as _sf:
            _configured = _json.load(_sf).get('tesseract_path', '')
            if _configured and os.path.isdir(_configured):
                _tess_dir = _configured
    except Exception:
        pass
    if os.path.isdir(_tess_dir):
        for _f in _glob.glob(os.path.join(_tess_dir, '*.exe')) + _glob.glob(os.path.join(_tess_dir, '*.dll')):
            _tess_datas.append((_f, 'tesseract'))
        _tessdata_dir = os.path.join(_tess_dir, 'tessdata')
        for _lang in ['eng', 'osd', 'jpn']:
            _td = os.path.join(_tessdata_dir, f'{_lang}.traineddata')
            if os.path.isfile(_td):
                _tess_datas.append((_td, 'tesseract/tessdata'))
elif sys.platform == 'darwin':
    try:
        _brew = _sp.check_output(['brew', '--prefix'], text=True).strip()
        _tess_exe = os.path.join(_brew, 'bin', 'tesseract')
        if os.path.isfile(_tess_exe):
            _tess_datas.append((_tess_exe, 'tesseract'))
        _tessdata_dir = os.path.join(_brew, 'share', 'tessdata')
        for _lang in ['eng', 'osd', 'jpn']:
            _td = os.path.join(_tessdata_dir, f'{_lang}.traineddata')
            if os.path.isfile(_td):
                _tess_datas.append((_td, 'tesseract/tessdata'))
    except Exception:
        pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # ttkthemesのテーマファイルのみ（他のデータはexeと同階層に外出し）
    ] + ttkthemes_datas + _tess_datas,
    hiddenimports=[
        # update_home_data() / update_battle_data() 内で動的にインポートされる
        'stats.home',
        'stats.search',
        # PIL + Tkinter 連携
        'PIL._tkinter_finder',
        # websockets の遅延ロードモジュール
        'websockets.legacy',
        'websockets.legacy.client',
        'websockets.legacy.server',
        'websockets.legacy.protocol',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='champedge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='champedge',
)
