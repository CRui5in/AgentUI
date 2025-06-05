@echo off
chcp 65001 >nul
echo 安装多功能 AI 应用依赖...

echo.
echo 1. 检查环境...
python check_env.py
if %errorlevel% neq 0 (
    echo 环境检查失败，请先解决环境问题
    pause
    exit /b 1
)

echo.
echo 2. 安装后端依赖...
cd backend
poetry install
if %errorlevel% neq 0 (
    echo 后端依赖安装失败
    pause
    exit /b 1
)

echo.
echo 3. 安装 AI Agent 核心依赖...
cd ..\agent_core
poetry install
if %errorlevel% neq 0 (
    echo Agent 核心依赖安装失败
    pause
    exit /b 1
)

echo.
echo 4. 安装 PPT 生成器依赖...
cd ..\tool_services\ppt_generator_service
poetry install
if %errorlevel% neq 0 (
    echo PPT 生成器依赖安装失败
    pause
    exit /b 1
)

echo.
echo 5. 安装图表生成器依赖...
cd ..\chart_generator_service
poetry install
if %errorlevel% neq 0 (
    echo 图表生成器依赖安装失败
    pause
    exit /b 1
)

echo.
echo 6. 安装前端依赖...
cd ..\..\frontend
npm install
if %errorlevel% neq 0 (
    echo 前端依赖安装失败
    pause
    exit /b 1
)

echo.
echo 7. 安装桌面应用依赖...
cd ..\desktop
npm install
if %errorlevel% neq 0 (
    echo 桌面应用依赖安装失败
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo 所有依赖安装完成！
echo ========================================
echo.
echo 下一步：
echo 1. 配置环境变量：
echo    - 复制 backend\env.example 到 backend\.env
echo    - 复制 agent_core\env.example 到 agent_core\.env
echo    - 编辑 .env 文件，配置 API 密钥
echo.
echo 2. 启动应用：
echo    - 运行 start_dev.bat
echo.
pause 