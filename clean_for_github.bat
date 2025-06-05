@echo off
chcp 65001 >nul
title 🧹 GitHub 上传前项目清理工具

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  🧹 GitHub 上传前项目清理工具                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🔍 开始清理项目文件...
echo.

echo 📁 清理 Python 缓存文件...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo   删除: %%d
        rmdir /s /q "%%d" 2>nul
    )
)

echo   删除 .pyc 文件...
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul

echo ✅ Python 缓存清理完成
echo.

echo 📁 清理 Node.js 依赖...
if exist "frontend\node_modules" (
    echo   删除: frontend\node_modules
    rmdir /s /q "frontend\node_modules" 2>nul
)

if exist "desktop\node_modules" (
    echo   删除: desktop\node_modules
    rmdir /s /q "desktop\node_modules" 2>nul
)

echo   删除 package-lock.json 文件...
del /q "frontend\package-lock.json" 2>nul
del /q "desktop\package-lock.json" 2>nul

echo ✅ Node.js 依赖清理完成
echo.

echo 📁 清理构建文件...
if exist "frontend\build" (
    echo   删除: frontend\build
    rmdir /s /q "frontend\build" 2>nul
)

if exist "frontend\dist" (
    echo   删除: frontend\dist
    rmdir /s /q "frontend\dist" 2>nul
)

if exist "desktop\dist" (
    echo   删除: desktop\dist
    rmdir /s /q "desktop\dist" 2>nul
)

if exist "desktop\build" (
    echo   删除: desktop\build
    rmdir /s /q "desktop\build" 2>nul
)

echo ✅ 构建文件清理完成
echo.

echo 📁 清理数据库文件...
del /q "backend\*.db" 2>nul
del /q "backend\*.sqlite" 2>nul
del /q "backend\*.sqlite3" 2>nul
del /q "agent_core\*.db" 2>nul
del /q "agent_core\*.sqlite" 2>nul
del /q "agent_core\*.sqlite3" 2>nul

echo ✅ 数据库文件清理完成
echo.

echo 📁 清理日志文件...
if exist "logs" (
    echo   删除: logs 目录
    rmdir /s /q "logs" 2>nul
)

del /s /q *.log 2>nul

echo ✅ 日志文件清理完成
echo.

echo 📁 清理上传文件...
if exist "backend\uploads" (
    echo   删除: backend\uploads
    rmdir /s /q "backend\uploads" 2>nul
    mkdir "backend\uploads" 2>nul
    echo.> "backend\uploads\.gitkeep"
)

echo ✅ 上传文件清理完成
echo.

echo 📁 清理缓存目录...
if exist ".cache" (
    echo   删除: .cache
    rmdir /s /q ".cache" 2>nul
)

if exist "cache" (
    echo   删除: cache
    rmdir /s /q "cache" 2>nul
)

if exist "tmp" (
    echo   删除: tmp
    rmdir /s /q "tmp" 2>nul
)

if exist "temp" (
    echo   删除: temp
    rmdir /s /q "temp" 2>nul
)

echo ✅ 缓存目录清理完成
echo.

echo 📁 清理虚拟环境...
if exist ".venv" (
    echo   删除: .venv
    rmdir /s /q ".venv" 2>nul
)

if exist "venv" (
    echo   删除: venv
    rmdir /s /q "venv" 2>nul
)

if exist "env" (
    echo   删除: env
    rmdir /s /q "env" 2>nul
)

echo ✅ 虚拟环境清理完成
echo.

echo 📁 清理 IDE 文件...
if exist ".vscode" (
    echo   删除: .vscode
    rmdir /s /q ".vscode" 2>nul
)

if exist ".idea" (
    echo   删除: .idea
    rmdir /s /q ".idea" 2>nul
)

del /q *.code-workspace 2>nul
del /q *.iml 2>nul

echo ✅ IDE 文件清理完成
echo.

echo 📁 清理系统文件...
del /s /q Thumbs.db 2>nul
del /s /q .DS_Store 2>nul
del /s /q desktop.ini 2>nul

echo ✅ 系统文件清理完成
echo.

echo 📁 清理生成的文件...
del /s /q *.pptx 2>nul
del /s /q *.ppt 2>nul

if exist "generated_files" (
    echo   删除: generated_files
    rmdir /s /q "generated_files" 2>nul
)

if exist "output" (
    echo   删除: output
    rmdir /s /q "output" 2>nul
)

echo ✅ 生成文件清理完成
echo.

echo 🔒 检查敏感配置文件...
if exist "agent_core\config.yaml" (
    echo ⚠️  注意: agent_core\config.yaml 包含配置信息
    echo    请确保删除其中的 API 密钥等敏感信息！
)

if exist "backend\config.yaml" (
    echo ⚠️  注意: backend\config.yaml 包含配置信息
    echo    请确保删除其中的 API 密钥等敏感信息！
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        🎉 清理完成！                         ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║  ✅ Python 缓存文件已清理                                    ║
echo ║  ✅ Node.js 依赖已清理                                       ║
echo ║  ✅ 构建文件已清理                                           ║
echo ║  ✅ 数据库文件已清理                                         ║
echo ║  ✅ 日志文件已清理                                           ║
echo ║  ✅ 上传文件已清理                                           ║
echo ║  ✅ 缓存目录已清理                                           ║
echo ║  ✅ 虚拟环境已清理                                           ║
echo ║  ✅ IDE 文件已清理                                           ║
echo ║  ✅ 系统文件已清理                                           ║
echo ║  ✅ 生成文件已清理                                           ║
echo ║                                                              ║
echo ║  📝 下一步操作:                                              ║
echo ║  1. 检查并清理配置文件中的敏感信息                           ║
echo ║  2. 确认 .gitignore 文件已创建                               ║
echo ║  3. 运行 git add . 添加文件                                  ║
echo ║  4. 运行 git commit -m "Initial commit"                      ║
echo ║  5. 推送到 GitHub                                            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 💡 提示: 项目已准备好上传到 GitHub！
echo.
pause 