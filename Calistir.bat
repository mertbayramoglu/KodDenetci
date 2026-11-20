@echo off
chcp 65001 >nul
cd /d "%~dp0"

python -c "import tkinter" >nul 2>nul
if not errorlevel 1 goto run_python
py -3 -c "import tkinter" >nul 2>nul
if not errorlevel 1 goto run_py

echo Calisan bir Python bulunamadi. python.org'dan Python 3.9+ kurun
echo veya build_exe.bat ile olusturulan KodDenetci.exe dosyasini kullanin.
pause
exit /b 1

:run_python
where pythonw >nul 2>nul
if not errorlevel 1 (start "" pythonw KodDenetci.py) else (start "" python KodDenetci.py)
exit /b 0

:run_py
where pyw >nul 2>nul
if not errorlevel 1 (start "" pyw -3 KodDenetci.py) else (start "" py -3 KodDenetci.py)
exit /b 0
