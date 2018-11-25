@echo off
echo Check if Inno Setup is installed with pre-compiler in the folder used here.
echo ---
pause
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
"C:\Program Files (x86)\Inno Setup 5\ISCC.exe" /DMyAppVersion="%mydate%" create_setup.iss