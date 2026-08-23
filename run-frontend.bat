@echo off
title DKC57-Frontend
cd /d "%~dp0frontend"
echo Starting DKC 57 frontend on http://localhost:5000 ...
call npm start
echo.
echo Frontend stopped.
pause
