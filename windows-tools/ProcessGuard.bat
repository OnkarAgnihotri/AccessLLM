@echo off
:: Double-click to start ProcessGuard. Extra options are passed through, e.g.:
::   ProcessGuard.bat -RamAlertPercent 80 -GraceSeconds 30
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ProcessGuard.ps1" %*
