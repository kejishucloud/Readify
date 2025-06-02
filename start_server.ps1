# Readify 智能阅读助手启动脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "        Readify 智能阅读助手" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "正在激活conda环境DL..." -ForegroundColor Yellow
conda activate DL

Write-Host ""
Write-Host "正在检查项目状态..." -ForegroundColor Yellow
python check_status.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ 项目状态检查失败，请检查配置" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

Write-Host ""
Write-Host "🚀 启动Django开发服务器..." -ForegroundColor Green
Write-Host "访问地址: http://localhost:8000" -ForegroundColor Green
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

python manage.py runserver 0.0.0.0:8000 