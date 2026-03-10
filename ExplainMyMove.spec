# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['chess', 'chess.engine', 'chess.pgn', 'chess.svg', 'game_statistics', 'pgn_annotator']
hiddenimports += collect_submodules('chess')


a = Analysis(
    ['explain_my_move.py'],
    pathex=[],
    binaries=[],
    datas=[('stockfish\\stockfish-windows-x86-64-avx2.exe', 'stockfish')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ExplainMyMove',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
