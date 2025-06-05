"""
任务相关的 Pydantic 模式定义
用于 API 请求和响应的数据验证
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """任务基础模式"""
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    tool_type: str = Field(..., description="工具类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务参数")


class TaskCreate(TaskBase):
    """创建任务的请求模式"""
    pass


class TaskUpdate(BaseModel):
    """更新任务的请求模式"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskResponse(TaskBase):
    """任务响应模式"""
    id: UUID
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    user_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class TaskStats(BaseModel):
    """任务统计模式"""
    total: int = Field(..., description="总任务数")
    completed: int = Field(..., description="已完成任务数")
    pending: int = Field(..., description="待处理任务数")
    failed: int = Field(..., description="失败任务数") 