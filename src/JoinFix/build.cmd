@echo off
rem Requires LLVM-MinGW (winget install MartinStorsjo.LLVM-MinGW.UCRT). Builds a 32-bit .asi (the game is x86).
rem DOA5LR-JoinFix : release build (no log, -DNO_LOG) + -debug build (log DOA5LR-JoinFix.log + KeyTest), VERSIONINFO.
setlocal
cd /d "%~dp0"
set "BIN="
for /d %%P in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW*") do for /d %%D in ("%%P\llvm-mingw-*") do if exist "%%D\bin\i686-w64-mingw32-gcc.exe" set "BIN=%%D\bin"
if not defined BIN (echo LLVM-MinGW not found. Install it:  winget install MartinStorsjo.LLVM-MinGW.UCRT & exit /b 1)
"%BIN%\i686-w64-mingw32-windres.exe" -O coff -o version.res version.rc || (echo WINDRES FAILED & exit /b 1)
"%BIN%\i686-w64-mingw32-gcc.exe" -O2 -s -shared -static -Wall -Wl,--no-insert-timestamp -DNO_LOG -o DOA5LR-JoinFix.asi joinfix.c version.res || (echo BUILD release FAILED & exit /b 1)
"%BIN%\i686-w64-mingw32-gcc.exe" -O2 -s -shared -static -Wall -Wl,--no-insert-timestamp -o DOA5LR-JoinFix-debug.asi joinfix.c version.res || (echo BUILD debug FAILED & exit /b 1)
del version.res
for %%F in (DOA5LR-JoinFix.asi DOA5LR-JoinFix-debug.asi) do echo OK  %%F  %%~zF bytes
