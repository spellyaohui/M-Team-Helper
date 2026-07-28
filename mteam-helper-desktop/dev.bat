@echo off
chcp 65001 >nul
echo ========================================
echo M-Team Helper 桌面版 - 开发模式
echo ========================================
echo.

:: 检查依赖
if not exist node_modules (
    echo 安装依赖...
    call npm install
)

:: 启动后端（在新窗口）
echo 启动后端服务...
start "M-Team Backend" cmd /c "cd ..\mteam-helper\backend && python main.py"

:: 等待后端启动
echo 等待后端启动...
timeout /t 3 /nobreak >nul

:: 启动 Electron
echo 启动 Electron...
call npm start
