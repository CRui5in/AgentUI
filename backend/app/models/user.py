"""
用户数据模型
定义用户相关的数据库表结构
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    用户模型
    存储用户账户信息
    """
    __tablename__ = "users"

    # 主键
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # 用户信息
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名"
    )
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱地址"
    )
    
    full_name = Column(
        String(100),
        nullable=True,
        comment="全名"
    )
    
    # 密码哈希
    hashed_password = Column(
        String(255),
        nullable=False,
        comment="密码哈希"
    )
    
    # 状态
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活"
    )
    
    is_superuser = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否超级用户"
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
    
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        } 