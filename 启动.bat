@echo off
chcp 65001 >nul
echo ========================================
echo       请假管理系统 启动器
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 创建虚拟环境
echo [1/3] 正在创建虚拟环境...
if not exist "venv" (
    python -m venv venv
)

:: 安装依赖
echo [2/3] 正在安装依赖...
call venv\Scripts\pip install -q gradio plotly

:: 启动应用
echo [3/3] 正在启动应用...
echo.
echo 请在浏览器打开: http://127.0.0.1:7860
echo 按 Ctrl+C 停止服务
echo.
call venv\Scripts\python app.py

pause
