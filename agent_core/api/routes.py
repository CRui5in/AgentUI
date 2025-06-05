"""
AI Agent 核心 API 路由
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

# 创建路由器
router = APIRouter()


@router.post("/tasks")
async def submit_task(
    request: Request,
    task_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    提交任务给 Agent 处理（异步）
    """
    try:
        import asyncio
        
        agent_manager = request.app.state.agent_manager
        
        task_id = task_data.get("task_id")
        task_info = task_data.get("task_data", {})
        
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少 task_id")
        
        logger.info(f"📥 接收任务: {task_id}")
        
        # 检查Agent管理器是否已经初始化
        if not agent_manager.running:
            logger.warning(f"⏳ Agent初始化中，任务排队: {task_id}")
            return {
                "success": True,
                "task_id": task_id,
                "message": "任务已接收，Agent正在初始化中，任务将稍后处理"
            }
        
        # 异步处理任务，不等待完成，并且捕获所有异常避免阻塞
        async def safe_process_task():
            try:
                await agent_manager.process_task(task_id, task_info)
            except Exception as e:
                logger.error(f"❌ 任务处理异常: {task_id} - {e}")
        
        asyncio.create_task(safe_process_task())
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已接收，正在后台处理"
        }
    
    except Exception as e:
        logger.error(f"提交任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    request: Request
) -> Dict[str, Any]:
    """
    取消任务
    """
    try:
        agent_manager = request.app.state.agent_manager
        
        result = await agent_manager.cancel_task(str(task_id))
        
        return {
            "success": True,
            "task_id": str(task_id),
            "message": "任务已取消",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: UUID,
    request: Request
) -> Dict[str, Any]:
    """
    获取任务状态
    """
    try:
        agent_manager = request.app.state.agent_manager
        
        status = await agent_manager.get_task_status(str(task_id))
        
        return {
            "success": True,
            "task_id": str(task_id),
            "status": status
        }
    
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/llm/reload")
async def reload_llm_config(request: Request) -> Dict[str, Any]:
    """
    重新加载LLM配置
    """
    try:
        agent_manager = request.app.state.agent_manager
        
        result = await agent_manager.reload_llm_config()
        
        return {
            "success": True,
            "message": "LLM配置重新加载完成",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"重新加载LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/llm/status")
async def get_llm_status(request: Request) -> Dict[str, Any]:
    """
    获取LLM配置状态
    """
    try:
        agent_manager = request.app.state.agent_manager
        
        status = agent_manager.get_llm_status()
        
        return {
            "success": True,
            "status": status
        }
    
    except Exception as e:
        logger.error(f"获取LLM状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """
    健康检查
    """
    try:
        agent_manager = request.app.state.agent_manager
        llm_status = agent_manager.get_llm_status()
        
        return {
            "success": True,
            "status": "healthy",
            "agent_running": agent_manager.running,
            "llm_configured": llm_status.get("configured", False),
            "services": {
                "mcp_clients": len(agent_manager.mcp_clients),
                "active_tasks": len(agent_manager.tasks)
            }
        }
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 