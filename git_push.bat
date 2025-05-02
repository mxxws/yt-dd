@echo off
chcp 65001 >nul
echo 启动GitHub自动推送脚本...
echo.

set /p commitMessage=请输入提交信息: 

powershell -ExecutionPolicy Bypass -File "%~dp0git_push.ps1" "%commitMessage%"

echo.
echo 按任意键退出...
pause > nul 