@echo off
rem Builds DOA5LR-Salons-Installer.exe with the C# compiler shipped in Windows (.NET Framework 4.8, no SDK needed).
rem   build.cmd        -> unsigned build
rem   build.cmd sign   -> build + self-signed Authenticode signature (sign.ps1, needs pwsh 7)
setlocal
cd /d "%~dp0"
set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
set ICO=
if exist installer.ico set ICO=/win32icon:installer.ico
"%CSC%" /nologo /target:winexe /platform:x86 /optimize+ /warn:0 /out:DOA5LR-Salons-Installer.exe %ICO% /win32manifest:app.manifest ^
  /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll Installer.cs
if errorlevel 1 (echo BUILD FAILED & exit /b 1)
for %%F in (DOA5LR-Salons-Installer.exe) do echo OK  %%~nxF  %%~zF bytes
if /i "%~1"=="sign" call "%~dp0sign.cmd" DOA5LR-Salons-Installer.exe
