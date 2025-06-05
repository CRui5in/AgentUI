@echo off
chcp 65001 >nul
title 🛑 停止多功能 AI 应用

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🛑 停止多功能 AI 应用                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🔍 正在停止所有服务...
echo.

echo 📊 停止后端服务 (端口 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 🤖 停止 AI Agent 核心 (端口 8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 📄 停止 PPT 生成服务 (端口 8002)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8002"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 📈 停止图表生成服务 (端口 8003)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8003"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 📅 停止日程提醒服务 (端口 8004)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8004"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 📚 停止API文档生成服务 (端口 8005)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8005"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 🎨 停止前端应用 (端口 4396)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":4396"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ✅ 所有服务已停止
echo.

echo 🔍 检查剩余进程...
netstat -ano | findstr ":800" | findstr "LISTENING"
if %errorlevel% equ 0 (
    echo ⚠️  仍有端口被占用，可能需要手动清理
) else (
    echo ✅ 所有端口已释放
)

echo.
echo 🎉 停止完成！
pause 