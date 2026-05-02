# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ttkthemes のテーマファイル（.tcl / 画像）を取得
ttkthemes_datas = collect_data_files('ttkthemes')

# Windows のみ favicon.ico を適用（macOS は ICNS が必要なので未指定）
_icon = 'image/favicon.ico' if sys.platform == 'win32' else None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('version.txt',        '.'),
        ('image',              'image'),
        ('database/pokemon.db','database'),
        ('database/battle.db', 'database'),
        ('stats',              'stats'),
        ('recog/recogImg',     'recog/recogImg'),
        ('recog/outputImg',    'recog/outputImg'),
        ('recog/capture.json', 'recog'),
        ('recog/setting.json', 'recog'),
        ('recog/coordinate.json', 'recog'),
        ('party/csv',          'party/csv'),
        ('party/txt',          'party/txt'),
        ('party/table',        'party/table'),
        ('party/setting.txt',  'party'),
    ] + ttkthemes_datas,
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
