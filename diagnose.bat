@echo off
setlocal
cd /d "%~dp0"
title ETHUSDT Monitor Diagnostics
echo ===== ETHUSDT MONITOR DIAGNOSTICS =====
echo Date/time:
echo %date% %time%
echo.
echo ===== PYTHON =====
where py
where python
py --version 2>&1
python --version 2>&1
echo.
echo ===== VENV =====
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version
  ".venv\Scripts\python.exe" -m pip show streamlit
) else (
  echo .venv does not exist
)
echo.
echo ===== PORT 8501 =====
netstat -ano | findstr :8501
echo.
echo ===== QUICK APP START TEST =====
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
streamlit version 2>&1
echo.
echo If there is an error above, copy this window text or take a screenshot and send it to ChatGPT.
pause
