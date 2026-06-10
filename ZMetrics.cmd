@echo off
rem Двойной клик = запуск десктоп-приложения ZMetrics.
rem Аргументы пробрасываются в скрипт: ZMetrics.cmd -WithStack
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_desktop.ps1" %*
