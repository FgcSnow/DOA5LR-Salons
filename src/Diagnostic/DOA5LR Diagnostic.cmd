@echo off
rem DOA5LR-Salons - Diagnostic : verifier, jouer avec la sonde, envoyer ses logs. / Check, play with the probe, send your logs.
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%~dp0DOA5LR-Diagnostic.ps1"
