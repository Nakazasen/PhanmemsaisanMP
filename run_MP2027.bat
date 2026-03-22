@echo off
title MP2027 Manager - Universal GUI
echo --------------------------------------------------
echo   MP2027 Manager (V3.0 - Standalone GUI)
echo   He thong lap ngan sach tu dong - Nakazato
echo --------------------------------------------------
echo.
echo Dang khoi dong Giao dien...
py src/universal_app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Khong the khoi dong ung dung. 
    echo Vui long kiem tra lai cai dat Python (py).
    pause
)
pause
