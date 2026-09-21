@echo off
rem Requires LLVM-MinGW (winget install MartinStorsjo.LLVM-MinGW.UCRT). Builds a 32-bit .asi (the game is x86).
rem DOA5LR-InviteFix : build release (sans journal, -DNO_LOG) + build debug (journal DOA5LR-InviteFix.log), avec VERSIONINFO.
setlocal
cd /d "%~dp0"
set "BIN="
if defined LLVM_MINGW if exist "%LLVM_MINGW%\bin\i686-w64-mingw32-gcc.exe" set "BIN=%LLVM_MINGW%\bin"
if not defined BIN for /f "delims=" %%P in ('where i686-w64-mingw32-gcc.exe 2^>nul') do if not defined BIN set "BIN=%%~dpP"
if not defined BIN for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW*\llvm-mingw-*") do if exist "%%D\bin\i686-w64-mingw32-gcc.exe" set "BIN=%%D\bin"
if not defined BIN (echo LLVM-MinGW not found. Install it:  winget install MartinStorsjo.LLVM-MinGW.UCRT   ^(or set LLVM_MINGW=^<its folder^>^) & exit /b 1)
if "%BIN:~-1%"=="\" set "BIN=%BIN:~0,-1%"
set "GCC=%BIN%\i686-w64-mingw32-gcc.exe"
set "RES=%BIN%\i686-w64-mingw32-windres.exe"
"%RES%" -O coff -o version.res version.rc || (echo WINDRES FAILED & exit /b 1)
"%GCC%" -O2 -s -shared -static -Wl,--no-insert-timestamp -DNO_LOG -o DOA5LR-InviteFix.asi invitefix.c version.res || (echo BUILD release FAILED & exit /b 1)
"%GCC%" -O2 -s -shared -static -Wl,--no-insert-timestamp -o DOA5LR-InviteFix-debug.asi invitefix.c version.res || (echo BUILD debug FAILED & exit /b 1)
del version.res
for %%F in (DOA5LR-InviteFix.asi DOA5LR-InviteFix-debug.asi) do echo OK  %%F  %%~zF bytes
exit /b 0
