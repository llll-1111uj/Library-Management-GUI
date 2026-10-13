@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm library.spec
echo.
echo Output: dist\LibraryManagement\LibraryManagement.exe
endlocal
