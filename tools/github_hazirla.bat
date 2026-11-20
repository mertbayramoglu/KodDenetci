@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === Kod Denetci - GitHub hazirlik ===

where git >nul 2>nul
if errorlevel 1 goto nogit

if exist docs\ci.yml.txt (
  if not exist .github\workflows mkdir .github\workflows
  move /y docs\ci.yml.txt .github\workflows\ci.yml >nul
  echo [OK] CI dosyasi .github\workflows\ci.yml konumuna tasindi.
)

echo.
echo Testler calistiriliyor...
python -m unittest discover -s tests
if errorlevel 1 goto testfail

if not exist .git (
  git init
  git symbolic-ref HEAD refs/heads/main
)
git add .

set "LEAK="
for /f "delims=" %%i in ('git ls-files veri *.db') do set "LEAK=1"
if defined LEAK goto leak

echo.
echo Depoya eklenecek dosyalar:
git status --short
echo.
set "OK="
set /p OK=Bu dosyalar commit edilsin mi? (E/H): 
if /i not "%OK%"=="E" goto done
for /f "delims=" %%V in ('python -c "import kd_core;print(kd_core.APP_VER)" 2^>nul') do set KDVER=%%V
if "%KDVER%"=="" set KDVER=update
git commit -m "Kod Denetci %KDVER%"

echo.
set "URL="
set /p URL=GitHub depo adresi (bos birakirsan push atlanir): 
if "%URL%"=="" goto done
git remote remove origin >nul 2>nul
git remote add origin "%URL%"
git push -u origin main
goto done

:nogit
echo HATA: Git bulunamadi. https://git-scm.com adresinden kurun.
goto done
:testfail
echo HATA: Testler basarisiz. Duzeltmeden depoya gondermeyin.
goto done
:leak
echo HATA: veri klasoru veya .db dosyasi depoya eklenmis gorunuyor. Gonderim durduruldu.
echo Duzeltmek icin: git rm -r --cached veri
goto done
:done
echo.
pause
