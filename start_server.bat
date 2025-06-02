@echo off
echo ========================================
echo        Readify 智能阅读助手
echo ========================================
echo.

echo 正在激活conda环境DL...
call conda activate DL

echo.
echo 正在检查项目状态...
python check_status.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ 项目状态检查失败，请检查配置
    pause
    exit /b 1
)

echo.
echo 🚀 启动Django开发服务器...
echo 访问地址: http://localhost:8000
echo 按 Ctrl+C 停止服务器
echo.

python manage.py runserver 0.0.0.0:8000

pause 