@echo off
REM One-click: create the git repo and make the first commit.
REM Requires Git for Windows: https://git-scm.com/download/win
cd /d "%~dp0"
git init -b main
git config user.email "you@example.com"
git config user.name "Your Name"
git add -A
git commit -m "Initial commit: ADS RF automation toolkit (docs + scripts + examples)"
echo.
echo Done. To publish:
echo   git remote add origin https://github.com/<you>/ads-rf-automation.git
echo   git push -u origin main
pause
