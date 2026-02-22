# areteDemo.spec
# Run with: pyinstaller areteDemo.spec
# from inside the areteDemo/ folder

import os
from kivy_deps import sdl2, glew, angle

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.', '..'],
    binaries=[],
    datas=[
        ('main.kv', '.'),
        ('arete.db', '.'),
        ('images', 'images'),
    ],
    hiddenimports=[
        'areteDemo',
        'areteDemo.db',
        'areteDemo.auth',
        'areteDemo.screens',
        'areteDemo.screens.login',
        'areteDemo.screens.register',
        'areteDemo.screens.main_menu',
        'areteDemo.screens.profile',
        'areteDemo.screens.settings',
        'areteDemo.screens.game',
        'areteDemo.screens.help',
        'areteDemo.screens.reflection',
        'capstone_game_demo_kivy',
        'kivy',
        'kivy.core.window',
        'kivy.core.text',
        'kivy.core.image',
        'kivy.graphics',
        'kivy.uix.screenmanager',
        'kivy.uix.label',
        'kivy.uix.button',
        'kivy.uix.textinput',
        'kivy.uix.boxlayout',
        'kivy.uix.gridlayout',
        'kivy.uix.scrollview',
        'kivy.uix.popup',
        'kivy.uix.widget',
        'sqlite3',
    ],
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
    name='Arete',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins + angle.dep_bins)],
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Arete',
)
