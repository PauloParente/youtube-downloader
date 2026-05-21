# -*- mode: python ; coding: utf-8 -*-
# Build: .\build.ps1 (copia FFmpeg para dist apos PyInstaller)
# Output: dist/YouTubeDownloader/YouTubeDownloader.exe (+ ffmpeg/ via build.ps1)

from pathlib import Path

block_cipher = None
project_dir = Path(SPECPATH)
src_dir = project_dir / "src"

a = Analysis(
    [str(project_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        (
            str(src_dir / "youtube_downloader" / "resources" / "icons"),
            "youtube_downloader/resources/icons",
        ),
    ],
    hiddenimports=["PySide6", "shiboken6", "PySide6.QtSvg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YouTubeDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YouTubeDownloader",
)
