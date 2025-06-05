"""
AI Agent 核心服务主入口
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import time

from core.config import settings
from core.agent_manager import AgentManager
from api.routes import router

# 创建 FastAPI 应用
app = FastAPI(
    title="AI Agent 核心服务",
    description="智能任务处理和工具调用服务",
    version="1.0.0"
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录HTTP请求"""
    start_time = time.time()
    
    # 处理请求
    response = await call_next(request)
    
    # 记录所有请求
    process_time = time.time() - start_time
    logger.info(f"🤖 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建 Agent 管理器实例
agent_manager = AgentManager()


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🤖 Agent 核心服务启动完成")
    logger.info(f"🌐 服务地址: http://{settings.AGENT_HOST}:{settings.AGENT_PORT}")
    logger.info(f"🔗 后端地址: {settings.BACKEND_URL}")
    logger.info(f"🔧 调试模式: {'开启' if settings.DEBUG else '关闭'}")
    
    # 先将 Agent 管理器添加到应用状态，确保API可以访问
    app.state.agent_manager = agent_manager
    
    # 异步初始化 Agent 管理器，不阻塞HTTP服务器启动
    import asyncio
    asyncio.create_task(agent_manager.initialize())


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("关闭 AI Agent 核心服务...")
    
    # 关闭 Agent 管理器
    await agent_manager.shutdown()
    
    logger.info("AI Agent 核心服务已关闭")


# 注册路由
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI Agent 核心服务",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "ai-agent-core",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    # 启动信息
    logger.info("🤖 启动 Agent 核心服务...")
    
    uvicorn.run(
        "main:app",
        host=settings.AGENT_HOST,
        port=settings.AGENT_PORT,
        reload=settings.DEBUG,
        # 移除 log_level 参数，让 loguru 处理日志
        access_log=False  # 禁用 uvicorn 的访问日志，使用自定义日志
    ) 