@echo off
pyinstaller graphulator.spec
mkdir dist\graphulator\platforms
copy dist\graphulator\PyQt5\Qt\plugins\platforms dist\graphulator\platforms\