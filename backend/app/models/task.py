"""
任务数据模型
定义任务相关的数据库表结构
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class TaskStatus:
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    """
    任务模型
    存储 AI Agent 执行的任务信息
    """
    __tablename__ = "tasks"

    # 主键
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # 基本信息
    title = Column(String(255), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务描述")
    
    # 任务状态
    status = Column(
        Enum(
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            name="task_status"
        ),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
        comment="任务状态"
    )
    
    # 工具类型
    tool_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="工具类型"
    )
    
    # 参数和结果
    parameters = Column(
        JSON,
        nullable=True,
        comment="任务参数"
    )
    
    result = Column(
        JSON,
        nullable=True,
        comment="任务结果"
    )
    
    # 错误信息
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    
    # 执行信息
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始执行时间"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间"
    )
    
    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    
    # 用户关联 (可选)
    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="用户ID"
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "tool_type": self.tool_type,
            "parameters": self.parameters,
            "result": self.result,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": str(self.user_id) if self.user_id else None,
        } 