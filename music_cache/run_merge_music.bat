@echo off
REM ============================================================
REM run_merge_music.bat
REM Chay nhanh merge_music.sh bang cach double-click, khong can
REM tu mo Git Bash / go lenh tay.
REM
REM YEU CAU: da cai Git for Windows (co san Git Bash + bash.exe)
REM Neu chua co, tai tai: https://git-scm.com/download/win
REM ============================================================

setlocal

REM Chuyen ve dung thu muc chua file .bat nay (de chay dung dan
REM du ban double-click tu bat ky dau)
cd /d "%~dp0"

echo ============================================
echo   Dang tim Git Bash...
echo ============================================

REM ---- Cach 1: bash.exe co san trong PATH ----
where bash.exe >nul 2>nul
if %errorlevel%==0 (
    echo   -^> Tim thay bash trong PATH.
    bash merge_music.sh
    goto :end
)

REM ---- Cach 2: duong dan cai dat mac dinh cua Git for Windows ----
set "GITBASH=%ProgramFiles%\Git\bin\bash.exe"
if exist "%GITBASH%" (
    echo   -^> Tim thay Git Bash tai: %GITBASH%
    "%GITBASH%" merge_music.sh
    goto :end
)

set "GITBASH2=%ProgramFiles(x86)%\Git\bin\bash.exe"
if exist "%GITBASH2%" (
    echo   -^> Tim thay Git Bash tai: %GITBASH2%
    "%GITBASH2%" merge_music.sh
    goto :end
)

REM ---- Khong tim thay: bao loi ro rang ----
echo.
echo [LOI] Khong tim thay Git Bash (bash.exe) tren may nay.
echo       Hay cai Git for Windows truoc, tai tai:
echo       https://git-scm.com/download/win
echo       (Cai xong, chi can chay lai file .bat nay la duoc.)
echo.
pause
exit /b 1

:end
echo.
echo ============================================
echo   XONG. Nhan phim bat ky de dong cua so nay.
echo ============================================
pause
endlocal
