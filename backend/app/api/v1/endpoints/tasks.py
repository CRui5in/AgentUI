"""
任务管理 API 端点
提供任务的 CRUD 操作和状态管理
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from loguru import logger

from app.core.database import get_db
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate, TaskStats
from app.services.agent_service import AgentService

# 创建路由器
router = APIRouter()

# Agent 服务实例
agent_service = AgentService()


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    tool_type: Optional[str] = Query(None, description="工具类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    """
    获取任务列表
    支持分页和过滤
    """
    try:
        # 构建查询
        query = select(Task).order_by(desc(Task.created_at))
        
        # 添加过滤条件
        if tool_type:
            query = query.where(Task.tool_type == tool_type)
        if status:
            query = query.where(Task.status == status)
        
        # 添加分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return [TaskResponse.from_orm(task) for task in tasks]
    
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")


@router.get("/stats", response_model=TaskStats)
async def get_task_stats(
    db: AsyncSession = Depends(get_db)
) -> TaskStats:
    """
    获取任务统计信息
    """
    try:
        # 查询各状态的任务数量
        stats_query = select(
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == TaskStatus.COMPLETED, 1), else_=0)).label("completed"),
            func.sum(case((Task.status == TaskStatus.PENDING, 1), else_=0)).label("pending"),
            func.sum(case((Task.status == TaskStatus.RUNNING, 1), else_=0)).label("running"),
            func.sum(case((Task.status == TaskStatus.FAILED, 1), else_=0)).label("failed"),
        )
        
        result = await db.execute(stats_query)
        stats = result.first()
        
        return TaskStats(
            total=stats.total or 0,
            completed=stats.completed or 0,
            pending=(stats.pending or 0) + (stats.running or 0),
            failed=stats.failed or 0,
        )
    
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务统计失败")


@router.get("/recent", response_model=List[TaskResponse])
async def get_recent_tasks(
    limit: int = Query(10, ge=1, le=50, description="返回的记录数"),
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    """
    获取最近的任务
    """
    try:
        query = select(Task).order_by(desc(Task.created_at)).limit(limit)
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return [TaskResponse.from_orm(task) for task in tasks]
    
    except Exception as e:
        logger.error(f"获取最近任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取最近任务失败")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    获取单个任务详情
    """
    try:
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskResponse.from_orm(task)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务详情失败")


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    创建新任务
    """
    try:
        # 创建任务实例
        task = Task(
            title=task_data.title,
            description=task_data.description,
            tool_type=task_data.tool_type,
            parameters=task_data.parameters,
            status=TaskStatus.PENDING,
        )
        
        # 保存到数据库
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # 先返回任务响应，避免Greenlet错误
        task_response = TaskResponse.from_orm(task)
        
        # 异步提交任务给 Agent 执行
        try:
            logger.info(f"📤 提交任务给 Agent: {task.id}")
            success = await agent_service.submit_task(task.id, task_data.dict())
            
            if not success:
                logger.error(f"❌ Agent 服务连接失败: {task.id}")
                # 更新任务状态为失败
                task.status = TaskStatus.FAILED
                task.error_message = "无法连接到Agent服务，请检查Agent核心服务是否正常运行"
                await db.commit()
                await db.refresh(task)
                # 更新返回的任务响应
                task_response = TaskResponse.from_orm(task)
            else:
                logger.info(f"✅ 任务已提交给 Agent: {task.id}")
        except Exception as e:
            logger.error(f"❌ 提交任务异常: {task.id} - {e}")
            # 更新任务状态为失败
            task.status = TaskStatus.FAILED
            task.error_message = f"提交任务失败: {str(e)}"
            await db.commit()
            await db.refresh(task)
            # 更新返回的任务响应
            task_response = TaskResponse.from_orm(task)
        
        logger.info(f"创建任务成功: {task.id}")
        return task_response
    
    except Exception as e:
        await db.rollback()
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    更新任务信息
    """
    try:
        # 查询任务
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 更新字段
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        # 保存更改
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"更新任务成功: {task_id}")
        return TaskResponse.from_orm(task)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新任务失败: {e}")
        raise HTTPException(status_code=500, detail="更新任务失败")


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    重试失败的任务
    """
    try:
        # 查询任务
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status != TaskStatus.FAILED:
            raise HTTPException(status_code=400, detail="只能重试失败的任务")
        
        # 重置任务状态
        task.status = TaskStatus.PENDING
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        
        await db.commit()
        await db.refresh(task)
        
        # 重新提交任务给 Agent
        try:
            task_data = {
                "title": task.title,
                "description": task.description,
                "tool_type": task.tool_type,
                "parameters": task.parameters,
            }
            await agent_service.submit_task(task.id, task_data)
        except Exception as e:
            logger.warning(f"重新提交任务给 Agent 失败: {e}")
        
        logger.info(f"重试任务成功: {task_id}")
        return TaskResponse.from_orm(task)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"重试任务失败: {e}")
        raise HTTPException(status_code=500, detail="重试任务失败")


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    取消任务
    """
    try:
        # 查询任务
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="任务已完成或已取消")
        
        # 更新任务状态
        task.status = TaskStatus.CANCELLED
        await db.commit()
        await db.refresh(task)
        
        # 通知 Agent 取消任务
        try:
            await agent_service.cancel_task(task.id)
        except Exception as e:
            logger.warning(f"通知 Agent 取消任务失败: {e}")
        
        logger.info(f"取消任务成功: {task_id}")
        return TaskResponse.from_orm(task)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    删除任务
    """
    try:
        # 查询任务
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 删除任务
        await db.delete(task)
        await db.commit()
        
        logger.info(f"删除任务成功: {task_id}")
        return {"message": "任务删除成功"}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail="删除任务失败") 