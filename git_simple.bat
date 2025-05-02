@echo off
chcp 65001 >nul
echo 简化版GitHub推送工具

set /p commitMessage=请输入提交信息: 

powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0git_simple.ps1' '%commitMessage%'"

echo.
pause 