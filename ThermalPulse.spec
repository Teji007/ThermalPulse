# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/thermalpulse.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/app.ico', 'assets')],
    hiddenimports=[
        'win32api',
        'win32con',
        'win32com.client',
        'win32timezone',
        'win32service',
        'win32serviceutil',
        'win32pdh',
        'pywintypes',
        'PySide6.QtNetwork',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'PIL'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ThermalPulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    uac_admin=True,
    icon='assets/app.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='ThermalPulse',
)