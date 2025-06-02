@echo off
echo ========================================
echo           Readify 启动脚本
echo ========================================
echo.

echo 正在激活conda DL环境...
call conda activate DL

echo.
echo 正在启动Readify服务器...
echo 服务器地址: http://localhost:8000
echo 按 Ctrl+C 停止服务器
echo.

python manage.py runserver 0.0.0.0:8000

pause 