# -*- mode: python -*-

block_cipher = None

import skrf
import os

a = Analysis(['spectrumfitter.py'],
             pathex=['C:\\P13pt\\spectrumfitter'],
             binaries=[],
             datas=[(os.path.join(os.path.dirname(skrf.__file__), 'data/*.*'), 'skrf/data'),
		    ('audacity.png', '.')],
             hiddenimports=['scipy._lib.messagestream', 'lmfit'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='spectrumfitter',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='audacity.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='spectrumfitter')
