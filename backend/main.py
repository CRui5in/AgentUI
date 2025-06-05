"""
多功能 AI 应用后端服务主入口
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import time

from app.core.config import settings
from app.api.v1.api import api_router

# 创建 FastAPI 应用
app = FastAPI(
    title="多功能 AI 应用后端",
    description="提供任务管理、文件处理和系统监控功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    start_time = time.time()
    
    # 处理请求
    response = await call_next(request)
    
    # 记录所有请求
    process_time = time.time() - start_time
    logger.info(f"🔵 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # 静态目录不存在时忽略
    pass


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 后端服务启动完成")
    if settings.DEBUG:
        logger.info(f"🔧 调试模式已启用")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("关闭后端服务...")


# 注册 API 路由
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "多功能 AI 应用后端服务",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "ai-app-backend",
        "version": "1.0.0",
        "debug": settings.DEBUG
    }


if __name__ == "__main__":
    import uvicorn
    
    # 启动信息
    logger.info("🚀 启动后端服务...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        # 移除 log_level 参数，让 loguru 处理日志
        access_log=False  # 禁用 uvicorn 的访问日志，使用我们的中间件
    ) 