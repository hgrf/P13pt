@echo off
echo You should make sure you have the correct version of pandas:
echo     conda install pandas==0.20.3
pause
pyinstaller spectrumfitter.spec
mkdir dist\spectrumfitter\platforms
copy dist\spectrumfitter\PyQt5\Qt\plugins\platforms dist\spectrumfitter\platforms\