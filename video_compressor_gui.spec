# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['video_compressor_gui.py'],
    pathex=['C:\\Users\\junqiao3060\\Documents\\FilmProductionTools'],
    binaries=[],
    datas=[('bin/ffmpeg.exe', 'bin'), ('bin/ffprobe.exe', 'bin'), ('qr/avatar.png', 'qr'),('qr/B站.png', 'qr'), ('qr/快手.png', 'qr'), ('qr/抖音.png', 'qr'), ('qr/红书.png', 'qr'), ('qr/视频号.png', 'qr')],
    hiddenimports=[],
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
    name='H265视频批量压缩工具 by电不撕',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='FPT_favicon.ico'  # 指定图标文件
)
