@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul
pushd "%~dp0"
cl /nologo /std:c++17 /W4 /EHsc /MT TestEngine.cpp /Fe:TestEngine.exe
if errorlevel 1 (popd & exit /b 1)
"%~dp0TestEngine.exe"
set r=%errorlevel%
del TestEngine.obj TestEngine.exe 2>nul
popd
exit /b %r%
