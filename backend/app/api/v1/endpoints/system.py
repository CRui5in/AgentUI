"""
系统相关 API 端点
提供系统信息和健康检查功能
"""

import platform
import psutil
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.core.config import settings

# 创建路由器
router = APIRouter()


@router.get("/info", response_model=Dict[str, Any])
async def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    """
    try:
        # 获取系统基本信息
        system_info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free,
        }
        
        # 获取 CPU 信息
        cpu_info = {
            "count": psutil.cpu_count(),
            "percent": psutil.cpu_percent(interval=1),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
        }
        
        # 获取磁盘信息
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": (disk.used / disk.total) * 100,
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": system_info,
            "memory": memory_info,
            "cpu": cpu_info,
            "disk": disk_info,
            "uptime": datetime.now().isoformat(),  # 简化的运行时间
        }
    
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统信息失败")


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    系统健康检查
    """
    try:
        # 检查内存使用率
        memory = psutil.virtual_memory()
        memory_ok = memory.percent < 90
        
        # 检查 CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_ok = cpu_percent < 90
        
        # 检查磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_ok = disk_percent < 90
        
        # 总体健康状态
        overall_health = memory_ok and cpu_ok and disk_ok
        
        return {
            "status": "healthy" if overall_health else "warning",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "memory": {
                    "status": "ok" if memory_ok else "warning",
                    "usage_percent": memory.percent,
                },
                "cpu": {
                    "status": "ok" if cpu_ok else "warning",
                    "usage_percent": cpu_percent,
                },
                "disk": {
                    "status": "ok" if disk_ok else "warning",
                    "usage_percent": disk_percent,
                },
            },
            "version": "1.0.0",
            "environment": "development" if settings.DEBUG else "production",
        }
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        } 