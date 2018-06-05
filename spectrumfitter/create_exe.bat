@echo off
echo Check out conda-spec-file.txt for the recommended setup.
echo ---
pause
pyinstaller spectrumfitter.spec
mkdir dist\spectrumfitter\platforms
copy dist\spectrumfitter\PyQt5\Qt\plugins\platforms dist\spectrumfitter\platforms\