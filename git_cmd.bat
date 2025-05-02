@echo off
chcp 65001 >nul
echo 简化版GitHub推送工具(CMD版本)
echo.

set /p commitMessage=请输入提交信息: 

echo 添加文件...
git add .

echo 提交更改：%commitMessage%
git commit -m "%commitMessage%"

echo 推送到GitHub...
git push origin master

echo.
echo 完成!
echo.
pause 