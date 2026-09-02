@echo off
cd /d "%~dp0.."
title Gemini Web2API Proxy (:8081)
echo --------------------------------------------------
echo   Khoi dong Proxy Gemini Web cuc bo cho MP2027
echo   Cong mac dinh: 8081 (OpenAI-compatible API)
echo --------------------------------------------------
echo.

set PROXY_DIR=%~dp0..\gemini-web2api
if not exist "%PROXY_DIR%\gemini_web2api.py" (
    echo [LOI] Khong tim thay thu muc gemini-web2api tai:
    echo %PROXY_DIR%
    echo.
    echo Vui long kiem tra xem gemini-web2api da duoc dat canh MP2027 hay chua.
    pause
    exit /b 1
)

echo Dang khoi dong proxy tu: %PROXY_DIR%
cd /d "%PROXY_DIR%"
if exist "%PROXY_DIR%\.venv\Scripts\python.exe" (
    "%PROXY_DIR%\.venv\Scripts\python.exe" gemini_web2api.py --config config.json
) else (
    python gemini_web2api.py --config config.json
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Proxy da dung dot ngot (ma loi: %ERRORLEVEL%).
    pause
)
