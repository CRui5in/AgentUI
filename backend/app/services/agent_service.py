"""
Agent 服务模块
负责与 AI Agent 核心的通信和任务管理
"""

import asyncio
from typing import Dict, Any, Optional
from uuid import UUID

import httpx
from loguru import logger

from app.core.config import settings


class AgentService:
    """
    Agent 服务类
    处理与 AI Agent 核心的通信
    """
    
    def __init__(self):
        self.agent_url = settings.AGENT_CORE_URL
        self.timeout = 120.0
        self._config_service = None
    
    async def _get_agent_url(self) -> str:
        """
        动态获取Agent URL
        """
        try:
            if self._config_service is None:
                from app.services.config_service import ConfigService
                self._config_service = ConfigService()
            
            service_config = await self._config_service.get_service_config()
            agent_url = service_config.get("agent_url", self.agent_url)
            
            if agent_url != self.agent_url:
                logger.info(f"Agent URL 从配置文件更新: {self.agent_url} -> {agent_url}")
                self.agent_url = agent_url
            
            return agent_url
        except Exception as e:
            logger.warning(f"获取动态Agent URL失败，使用默认值: {e}")
            return self.agent_url
    
    async def submit_task(self, task_id: UUID, task_data: Dict[str, Any]) -> bool:
        """
        提交任务给 AI Agent 执行
        
        Args:
            task_id: 任务ID
            task_data: 任务数据
            
        Returns:
            bool: 提交是否成功
        """
        try:
            agent_url = await self._get_agent_url()
            logger.info(f"提交任务到 Agent: {task_id} -> {agent_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{agent_url}/api/tasks",
                    json={
                        "task_id": str(task_id),
                        "task_data": task_data,
                    }
                )
                response.raise_for_status()
                
                logger.info(f"任务提交成功: {task_id}")
                return True
                
        except httpx.RequestError as e:
            logger.error(f"Agent 网络错误: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent HTTP错误: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Agent 未知错误: {e}")
            return False
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """
        取消任务执行
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 取消是否成功
        """
        try:
            agent_url = await self._get_agent_url()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{agent_url}/api/tasks/{task_id}/cancel"
                )
                response.raise_for_status()
                
                logger.info(f"任务取消成功: {task_id}")
                return True
                
        except httpx.RequestError as e:
            logger.error(f"取消任务网络错误: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"取消任务HTTP错误: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"取消任务未知错误: {e}")
            return False
    
    async def get_task_status(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息
        """
        try:
            agent_url = await self._get_agent_url()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{agent_url}/api/tasks/{task_id}/status"
                )
                response.raise_for_status()
                
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"获取任务状态网络错误: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"获取任务状态HTTP错误: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"获取任务状态未知错误: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        检查 Agent 服务健康状态
        
        Returns:
            bool: 服务是否健康
        """
        try:
            agent_url = await self._get_agent_url()
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{agent_url}/health")
                response.raise_for_status()
                
                logger.info(f"Agent 服务健康检查成功: {agent_url}")
                return True
                
        except Exception as e:
            logger.warning(f"Agent 健康检查失败: {e}")
            return False 