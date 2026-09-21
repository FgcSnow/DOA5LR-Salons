@echo off
rem Builds every component of the pack (5 plugins with LLVM-MinGW, installer with the Windows C# compiler).
rem Outputs stay in each component folder. See README.md in this folder.
setlocal
cd /d "%~dp0"
set FAIL=0
for %%D in (InviteFix WiFi-Wired-Detector 60fps-menus Borderless UpdateCheck Installer) do (
    echo.
    echo === %%D
    call "%%D\build.cmd" || set FAIL=1
)
echo.
if "%FAIL%"=="1" (echo SOME BUILDS FAILED & exit /b 1)
echo ALL BUILDS OK
if /i "%~1"=="sign" (
    echo.
    echo === signing
    call "tools\sign.cmd" InviteFix\DOA5LR-InviteFix.asi WiFi-Wired-Detector\DOA5LR-WiFi-Wired-Detector.asi 60fps-menus\DOA5LR-60fps-menus.asi Borderless\DOA5LR-Borderless.asi UpdateCheck\DOA5LR-UpdateCheck.asi Installer\DOA5LR-Salons-Installer.exe
)
exit /b 0
