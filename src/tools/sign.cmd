@echo off
rem Signs the given files with the self-signed DOA5LR-Salons certificate (see sign.ps1). Example: sign.cmd DOA5LR-Salons-Installer.exe
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0sign.ps1" %*
