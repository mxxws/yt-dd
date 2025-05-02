# 简化版GitHub推送脚本
param(
    [Parameter(Mandatory=$true)]
    [string]$Message
)

# 添加所有文件
Write-Host "添加文件..." -ForegroundColor Yellow
git add .

# 提交更改
Write-Host "提交更改：$Message" -ForegroundColor Cyan
git commit -m "$Message"

# 推送到远程
Write-Host "推送到GitHub..." -ForegroundColor Green
git push origin master

Write-Host "完成!" -ForegroundColor Green 