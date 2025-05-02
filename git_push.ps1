# yt-dd GitHub自动推送脚本
# 使用方法: ./git_push.ps1 "更新说明消息"

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$CommitMessage
)

# 定义颜色函数
function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [string]$ForegroundColor = "White"
    )
    
    Write-Host $Message -ForegroundColor $ForegroundColor
}

# 显示脚本标题
Write-ColorOutput "=======================================" "Cyan"
Write-ColorOutput "      YT-DD GitHub 自动推送脚本        " "Cyan" 
Write-ColorOutput "=======================================" "Cyan"
Write-ColorOutput "" "White"

# 确保我们在正确的目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# 更新提交日志文件
$updateLogFile = "update_log.md"
$dateTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not (Test-Path $updateLogFile)) {
    Write-ColorOutput "创建更新日志文件..." "Yellow"
    "# YT-DD 更新日志" | Out-File -FilePath $updateLogFile -Encoding utf8
    "" | Out-File -FilePath $updateLogFile -Append -Encoding utf8
}

Write-ColorOutput "更新日志..." "Yellow"
"## $dateTime" | Out-File -FilePath $updateLogFile -Append -Encoding utf8
"" | Out-File -FilePath $updateLogFile -Append -Encoding utf8
"- $CommitMessage" | Out-File -FilePath $updateLogFile -Append -Encoding utf8
"" | Out-File -FilePath $updateLogFile -Append -Encoding utf8

# 获取当前Git状态
Write-ColorOutput "检查Git状态..." "Yellow"
$status = git status --porcelain

if ([string]::IsNullOrEmpty($status)) {
    Write-ColorOutput "没有文件更改，无需提交。" "Red"
    exit 0
}

# 显示更改的文件
Write-ColorOutput "以下文件将被提交:" "Green"
$status | ForEach-Object {
    $statusCode = $_.Substring(0, 2).Trim()
    $filePath = $_.Substring(2).Trim()
    
    if ($statusCode -eq "M") {
        Write-ColorOutput "  修改: $filePath" "Yellow"
    } elseif ($statusCode -eq "A" -or $statusCode -eq "??") {
        Write-ColorOutput "  新增: $filePath" "Green"
    } elseif ($statusCode -eq "D") {
        Write-ColorOutput "  删除: $filePath" "Red"
    } else {
        Write-ColorOutput "  ${statusCode}: $filePath" "White"
    }
}

Write-ColorOutput "" "White"
Write-ColorOutput "提交信息: $CommitMessage" "Cyan"
Write-ColorOutput "" "White"

# 确认提交
$confirmation = Read-Host "确认提交更改到GitHub? (Y/N)"
if ($confirmation -ne "Y" -and $confirmation -ne "y") {
    Write-ColorOutput "操作已取消。" "Red"
    exit 0
}

# 添加所有更改
Write-ColorOutput "添加更改到暂存区..." "Yellow"
git add .

# 提交更改
Write-ColorOutput "提交更改..." "Yellow"
git commit -m "$CommitMessage"

# 检查远程仓库是否已配置
$remotes = git remote
if ($remotes -notcontains "origin") {
    $gitUrl = Read-Host "请输入GitHub仓库URL (例如: https://github.com/username/yt-dd.git)"
    git remote add origin $gitUrl
}

# 推送到GitHub
Write-ColorOutput "推送到GitHub..." "Yellow"
git push origin master

if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "成功推送到GitHub!" "Green"
} else {
    Write-ColorOutput "推送失败，请检查错误信息。" "Red"
}

Write-ColorOutput "=======================================" "Cyan"
Write-ColorOutput "            操作完成                  " "Cyan"
Write-ColorOutput "=======================================" "Cyan" 