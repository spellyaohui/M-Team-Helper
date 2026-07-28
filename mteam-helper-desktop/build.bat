@echo off
chcp 65001 >nul
echo ========================================
echo M-Team Helper 桌面版构建脚本
echo ========================================
echo.

:: 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

:: 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/6] 清理旧的构建产物...
if exist dist rmdir /s /q dist
if exist frontend rmdir /s /q frontend
if exist backend-dist\mteam-backend.exe del /q backend-dist\mteam-backend.exe

echo.
echo [2/6] 安装 Electron 依赖...
call npm install
if %errorlevel% neq 0 (
    echo [错误] npm install 失败
    pause
    exit /b 1
)

echo.
echo [3/6] 生成应用图标...
if not exist icon.ico (
    call node scripts/generate-icon.js
)

echo.
echo [4/6] 构建前端...
call node scripts/build-frontend.js
if %errorlevel% neq 0 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)

echo.
echo [5/6] 构建后端...
cd ..\mteam-helper\backend
pip install -r requirements.txt -q
pip install pyinstaller -q
cd ..\..\mteam-helper-desktop
call node scripts/build-backend.js
if %errorlevel% neq 0 (
    echo [错误] 后端构建失败
    pause
    exit /b 1
)

echo.
echo [6/6] 打包 Electron 应用...
call npm run build:electron
if %errorlevel% neq 0 (
    echo [错误] Electron 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 构建完成！
echo 输出目录: dist\
echo - 安装包: M-Team Helper Setup 1.0.0.exe
echo - 便携版: MTeam-Helper-Portable-1.0.0.exe
echo ========================================
pause
