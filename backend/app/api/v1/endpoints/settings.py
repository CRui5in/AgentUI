"""
系统设置 API 端点
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings
from app.services.config_service import ConfigService

router = APIRouter()

# 配置服务实例
config_service = ConfigService()


class LLMConfigModel(BaseModel):
    """LLM配置模型"""
    provider: str = "openai"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2048


class DatabaseConfigModel(BaseModel):
    """数据库配置模型"""
    type: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    database: str = "ai_app.db"
    username: str = ""
    password: str = ""


class ServiceConfigModel(BaseModel):
    """服务配置模型"""
    backend_url: str = "http://localhost:8000"
    agent_url: str = "http://localhost:8001"
    ppt_service_url: str = "http://localhost:8002"
    chart_service_url: str = "http://localhost:8003"
    timeout: int = 30000


class AppConfigModel(BaseModel):
    """应用配置模型"""
    theme: str = "light"
    language: str = "zh-CN"
    auto_save: bool = True
    notifications: bool = True
    debug_mode: bool = False


class AllConfigsModel(BaseModel):
    """所有配置模型"""
    llm: LLMConfigModel
    database: DatabaseConfigModel
    service: ServiceConfigModel
    app: AppConfigModel


@router.get("/llm")
async def get_llm_config() -> Dict[str, Any]:
    """
    获取LLM配置
    """
    try:
        config = await config_service.get_llm_config()
        
        # 如果是新格式，直接返回
        if 'provider_configs' in config:
            return config
        
        # 向后兼容：转换旧格式为Agent期望的格式
        return {
            "provider": config.get("provider", "openai"),
            "api_key": config.get("api_key", ""),
            "base_url": config.get("base_url", ""),
            "model": config.get("model", "gpt-4"),
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 2048)
        }
    except Exception as e:
        logger.error(f"获取LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取LLM配置失败: {e}")


@router.post("/llm")
async def save_llm_config(config: LLMConfigModel) -> Dict[str, Any]:
    """
    保存LLM配置（向后兼容）
    """
    try:
        config_dict = {
            "provider": config.provider,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
        await config_service.save_llm_config(config_dict)
        
        return {
            "success": True,
            "message": "LLM配置保存成功"
        }
    except Exception as e:
        logger.error(f"保存LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存LLM配置失败: {e}")


@router.post("/llm/provider/{provider}")
async def save_provider_config(provider: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存单个提供商配置
    """
    try:
        await config_service.save_provider_config(provider, config_data)
        
        return {
            "success": True,
            "message": f"提供商 {provider} 配置保存成功"
        }
    except Exception as e:
        logger.error(f"保存提供商 {provider} 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存提供商配置失败: {e}")


@router.post("/llm/current/{provider}")
async def set_current_provider(provider: str) -> Dict[str, Any]:
    """
    设置当前使用的提供商
    """
    try:
        await config_service.set_current_provider(provider)
        
        return {
            "success": True,
            "message": f"当前LLM提供商设置为: {provider}"
        }
    except Exception as e:
        logger.error(f"设置当前提供商失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置当前提供商失败: {e}")


@router.get("/database")
async def get_database_config() -> Dict[str, Any]:
    """
    获取数据库配置
    """
    try:
        config = await config_service.get_database_config()
        return config
    except Exception as e:
        logger.error(f"获取数据库配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据库配置失败: {e}")


@router.post("/database")
async def save_database_config(config: DatabaseConfigModel) -> Dict[str, Any]:
    """
    保存数据库配置
    """
    try:
        config_dict = config.dict()
        await config_service.save_database_config(config_dict)
        
        return {
            "success": True,
            "message": "数据库配置保存成功"
        }
    except Exception as e:
        logger.error(f"保存数据库配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存数据库配置失败: {e}")


@router.get("/service")
async def get_service_config() -> Dict[str, Any]:
    """
    获取服务配置
    """
    try:
        config = await config_service.get_service_config()
        return config
    except Exception as e:
        logger.error(f"获取服务配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取服务配置失败: {e}")


@router.post("/service")
async def save_service_config(config: ServiceConfigModel) -> Dict[str, Any]:
    """
    保存服务配置
    """
    try:
        config_dict = config.dict()
        await config_service.save_service_config(config_dict)
        
        return {
            "success": True,
            "message": "服务配置保存成功"
        }
    except Exception as e:
        logger.error(f"保存服务配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存服务配置失败: {e}")


@router.get("/app")
async def get_app_config() -> Dict[str, Any]:
    """
    获取应用配置
    """
    try:
        config = await config_service.get_app_config()
        return config
    except Exception as e:
        logger.error(f"获取应用配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取应用配置失败: {e}")


@router.post("/app")
async def save_app_config(config: AppConfigModel) -> Dict[str, Any]:
    """
    保存应用配置
    """
    try:
        config_dict = config.dict()
        await config_service.save_app_config(config_dict)
        
        return {
            "success": True,
            "message": "应用配置保存成功"
        }
    except Exception as e:
        logger.error(f"保存应用配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存应用配置失败: {e}")


@router.get("/all")
async def get_all_configs() -> Dict[str, Any]:
    """
    获取所有配置
    """
    try:
        llm_config = await config_service.get_llm_config()
        database_config = await config_service.get_database_config()
        service_config = await config_service.get_service_config()
        app_config = await config_service.get_app_config()
        
        return {
            "llm": llm_config,
            "database": database_config,
            "service": service_config,
            "app": app_config
        }
    except Exception as e:
        logger.error(f"获取所有配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取所有配置失败: {e}")


@router.post("/all")
async def save_all_configs(configs: AllConfigsModel) -> Dict[str, Any]:
    """
    保存所有配置
    """
    try:
        await config_service.save_llm_config(configs.llm.dict())
        await config_service.save_database_config(configs.database.dict())
        await config_service.save_service_config(configs.service.dict())
        await config_service.save_app_config(configs.app.dict())
        
        return {
            "success": True,
            "message": "所有配置保存成功"
        }
    except Exception as e:
        logger.error(f"保存所有配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存所有配置失败: {e}")


@router.post("/test/{config_type}")
async def test_config(config_type: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试配置连接
    """
    try:
        if config_type == "llm":
            result = await config_service.test_llm_connection(config_data)
        elif config_type == "database":
            result = await config_service.test_database_connection(config_data)
        elif config_type == "service":
            result = await config_service.test_service_connection(config_data)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的配置类型: {config_type}")
        
        return {
            "success": result,
            "message": "连接测试成功" if result else "连接测试失败"
        }
    except Exception as e:
        logger.error(f"测试{config_type}配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试配置失败: {e}")


@router.post("/reload")
async def reload_configs() -> Dict[str, Any]:
    """
    重新加载配置
    """
    try:
        await config_service.reload_configs()
        
        return {
            "success": True,
            "message": "配置重新加载成功"
        }
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载配置失败: {e}") 


@router.get("/llm/models/{provider}")
async def get_available_models(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    获取指定提供商的可用模型列表
    """
    try:
        models = await config_service.get_available_models(provider, api_key, base_url)
        
        return {
            "success": True,
            "models": models
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return {
            "success": False,
            "models": [],
            "error": str(e)
        } 