# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['translator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt.windows.graphics.imaging',
        'winrt.windows.media.ocr',
        'winrt.windows.storage.streams',
        'winrt._winrt_windows_foundation',
        'winrt._winrt_windows_foundation_collections',
        'winrt._winrt_windows_graphics_imaging',
        'winrt._winrt_windows_media_ocr',
        'winrt._winrt_windows_storage_streams',
    ],
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
    name='translator',
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
