@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 启用ANSI颜色支持
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%VERSION%" == "10.0" (
    reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f > nul
)

:: 设置颜色
set "CYAN=[36m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "RESET=[0m"

:: 显示标题
echo %CYAN%=======================================%RESET%
echo %CYAN%      YT-DD GitHub 自动推送工具        %RESET%
echo %CYAN%=======================================%RESET%
echo.

:: 更新日志
set "logFile=update_log.md"
set "date=%date:~0,4%-%date:~5,2%-%date:~8,2% %time:~0,8%"

:: 检查日志文件是否存在
if not exist "%logFile%" (
    echo %YELLOW%创建更新日志文件...%RESET%
    echo # YT-DD 更新日志 > "%logFile%"
    echo. >> "%logFile%"
)

:: 获取提交信息
set /p commitMessage=请输入提交信息: 

:: 更新日志
echo %YELLOW%更新日志...%RESET%
echo ## %date% >> "%logFile%"
echo. >> "%logFile%"
echo - %commitMessage% >> "%logFile%"
echo. >> "%logFile%"

:: 获取git状态
echo %YELLOW%检查Git状态...%RESET%
git status --porcelain > git_status_temp.txt

:: 判断是否有文件更改
set "hasChanges=0"
for /f "delims=" %%i in (git_status_temp.txt) do (
    set "hasChanges=1"
)

if "%hasChanges%"=="0" (
    echo %RED%没有文件更改，无需提交。%RESET%
    del git_status_temp.txt
    goto :end
)

:: 显示将要提交的文件
echo %GREEN%以下文件将被提交:%RESET%
for /f "delims=" %%i in (git_status_temp.txt) do (
    set "status=%%i"
    set "statusCode=!status:~0,2!"
    set "filePath=!status:~3!"
    
    if "!statusCode!"==" M" (
        echo %YELLOW%  修改: !filePath!%RESET%
    ) else if "!statusCode!"=="??" (
        echo %GREEN%  新增: !filePath!%RESET%
    ) else if "!statusCode!"==" D" (
        echo %RED%  删除: !filePath!%RESET%
    ) else (
        echo   !statusCode!: !filePath!
    )
)

:: 删除临时文件
del git_status_temp.txt

echo.
echo %CYAN%提交信息: %commitMessage%%RESET%
echo.

:: 确认提交
set /p confirmation=确认提交更改到GitHub? (Y/N): 
if /i not "%confirmation%"=="Y" (
    echo %RED%操作已取消。%RESET%
    goto :end
)

:: 添加所有更改
echo %YELLOW%添加更改到暂存区...%RESET%
git add .

:: 提交更改
echo %YELLOW%提交更改...%RESET%
git commit -m "%commitMessage%"

:: 检查远程仓库是否已配置
git remote | findstr "origin" > nul
if errorlevel 1 (
    set /p gitUrl=请输入GitHub仓库URL (例如: https://github.com/username/yt-dd.git): 
    git remote add origin %gitUrl%
)

:: 推送到GitHub
echo %YELLOW%推送到GitHub...%RESET%
git push origin master

if %errorlevel% EQU 0 (
    echo %GREEN%成功推送到GitHub!%RESET%
) else (
    echo %RED%推送失败，请检查错误信息。%RESET%
)

:end
echo %CYAN%=======================================%RESET%
echo %CYAN%            操作完成                  %RESET%
echo %CYAN%=======================================%RESET%
echo.
pause 