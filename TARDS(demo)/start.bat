@echo off
chcp 65001 >nul
title Tards 启动器
cd /d "%~dp0"

echo ========================================
echo  Tards 卡牌对战游戏
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10 或更高版本。
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Python 已安装
python --version

:: 安装/更新依赖
echo [2/3] 检查并安装依赖...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接。
    pause
    exit /b 1
)

:: 启动游戏
echo [3/3] 启动游戏...
echo.
python Gamestart.py

if errorlevel 1 (
    echo.
    echo [错误] 游戏异常退出。
    pause
)
