@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x86
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /std:c++17 /O2 /MT /W4 /EHsc /LD ReplayTakeover.cpp /link /OUT:..\payload\DOA5LR-ReplayTakeover.asi
set result=%errorlevel%
del /q ReplayTakeover.obj ..\payload\DOA5LR-ReplayTakeover.exp ..\payload\DOA5LR-ReplayTakeover.lib 2>nul
popd
exit /b %result%
