@echo off
chcp 65001 >nul
title 🚀 多功能 AI 应用启动器

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🚀 多功能 AI 应用启动器                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🔍 检查依赖是否已安装...
cd backend
poetry run python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 后端依赖未安装，请先运行 install_deps.bat
    cd ..
    pause
    exit /b 1
)
cd ..

if not exist "frontend\node_modules" (
    echo ❌ 前端依赖未安装，请先运行 install_deps.bat
    pause
    exit /b 1
)

echo ✅ 依赖检查完成
echo.

echo 🎯 启动服务中...
echo.

echo 📊 1. 启动后端服务...
start "🔧 Backend API" cmd /k "cd backend && echo 启动后端服务... && poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3

echo 🤖 2. 启动 AI Agent 核心...
start "🧠 AI Agent" cmd /k "cd agent_core && echo 启动 AI Agent... && poetry run python main.py"

timeout /t 3

echo 🛠️ 3. 启动工具服务...
start "📄 PPT Service" cmd /k "cd tool_services/ppt_generator_service && echo 启动 PPT 生成服务... && poetry run python main.py"

timeout /t 2

start "📈 Chart Service" cmd /k "cd tool_services/chart_generator_service && echo 启动图表生成服务... && poetry run python main.py"

timeout /t 2

start "📅 Schedule Service" cmd /k "cd tool_services/schedule_reminder_service && echo 启动日程提醒服务... && poetry run python main.py"

timeout /t 2

start "📚 API Doc Service" cmd /k "cd tool_services/api_doc_generator_service && echo 启动API文档生成服务... && poetry run python main.py"

timeout /t 3

echo 🎨 4. 启动美化前端应用...
start "🌟 Frontend UI" cmd /k "cd frontend && echo 启动前端应用... && npm start"

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        🎉 启动完成！                         ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║  📱 前端应用:     http://localhost:4396                     ║
echo ║  🔧 后端 API:     http://localhost:8000/docs                ║
echo ║  🧠 Agent API:    http://localhost:8001/docs                ║
echo ║                                                              ║
echo ║  🛠️ 工具服务:                                                ║
echo ║    📄 PPT 生成器:     http://localhost:8002                 ║
echo ║    📈 图表生成器:     http://localhost:8003                 ║
echo ║    📅 日程提醒器:     http://localhost:8004                 ║
echo ║    📚 API文档生成器:  http://localhost:8005                 ║
echo ║                                                              ║
echo ║  🖥️ 桌面应用:     请运行 start_desktop.bat                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 💡 提示: 所有服务正在后台启动，请稍等片刻...
echo 🎯 新功能: 现在包含美化的界面和完整的配置管理！
echo.
pause 