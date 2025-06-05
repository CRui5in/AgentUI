"""
API v1 路由汇总
"""

from fastapi import APIRouter

from app.api.v1.endpoints import tasks, tools, upload, system, settings

# 创建 API 路由器
api_router = APIRouter()

# 注册各个端点路由
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(tools.router, prefix="/tools", tags=["工具配置"])
api_router.include_router(upload.router, prefix="/upload", tags=["文件上传"])
api_router.include_router(system.router, prefix="/system", tags=["系统监控"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])

# 为Agent兼容性添加config路由（映射到settings）
api_router.include_router(settings.router, prefix="/config", tags=["配置兼容"]) 