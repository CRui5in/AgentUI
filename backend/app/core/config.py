"""
应用配置模块
支持从 YAML 配置文件和环境变量加载配置
"""

import os
import yaml
from typing import List, Optional, Dict, Any
from pathlib import Path

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用设置类
    优先从 YAML 配置文件加载，然后从环境变量加载配置
    """
    
    # 基础配置
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_app.db"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:4396", "http://127.0.0.1:4396"]
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # LLM 提供商配置
    LLM_PROVIDERS: Dict[str, Any] = {}
    DEFAULT_LLM_PROVIDER: str = "openai"
    
    # 向后兼容的API密钥配置
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Agent 核心服务配置
    AGENT_CORE_URL: str = "http://localhost:8001"
    
    # MCP 服务器配置
    MCP_SERVERS: List[str] = [
        "http://localhost:8001",
        "http://localhost:8002", 
        "http://localhost:8003",
        "http://localhost:8004"
    ]
    
    # Celery 配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    def __init__(self, **kwargs):
        # 首先尝试从 YAML 配置文件加载
        yaml_config = self._load_yaml_config()
        
        # 将 YAML 配置合并到 kwargs 中（环境变量优先级更高）
        if yaml_config:
            for key, value in yaml_config.items():
                if key.upper() not in kwargs:
                    kwargs[key.upper()] = value
        
        super().__init__(**kwargs)
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """
        从 YAML 配置文件加载配置
        """
        config_file = Path(__file__).parent.parent.parent / "config.yaml"
        
        if not config_file.exists():
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 转换 YAML 配置为环境变量格式
            flat_config = {}
            
            # 服务器配置
            if 'server' in config:
                server = config['server']
                flat_config['DEBUG'] = server.get('debug', False)
            
            # 数据库配置
            if 'database' in config:
                db = config['database']
                flat_config['DATABASE_URL'] = db.get('url', "sqlite+aiosqlite:///./ai_app.db")
            
            # Redis 配置
            if 'redis' in config:
                redis = config['redis']
                flat_config['REDIS_URL'] = redis.get('url', "redis://localhost:6379/0")
            
            # CORS 配置
            if 'cors' in config:
                cors = config['cors']
                if 'origins' in cors:
                    flat_config['CORS_ORIGINS'] = cors['origins']
            
            # 文件上传配置
            if 'upload' in config:
                upload = config['upload']
                flat_config['UPLOAD_DIR'] = upload.get('directory', "./uploads")
                flat_config['MAX_FILE_SIZE'] = upload.get('max_file_size', 10485760)
            
            # 服务连接配置
            if 'services' in config:
                services = config['services']
                if 'agent_core' in services:
                    flat_config['AGENT_CORE_URL'] = services['agent_core'].get('url', "http://localhost:8001")
            
            # LLM 提供商配置
            if 'llm_providers' in config:
                flat_config['LLM_PROVIDERS'] = config['llm_providers']
                flat_config['DEFAULT_LLM_PROVIDER'] = config.get('default_llm_provider', 'openai')
                
                # 向后兼容的单一API密钥
                providers = config['llm_providers']
                if 'openai' in providers:
                    flat_config['OPENAI_API_KEY'] = providers['openai'].get('api_key')
                if 'anthropic' in providers:
                    flat_config['ANTHROPIC_API_KEY'] = providers['anthropic'].get('api_key')
                if 'gemini' in providers:
                    flat_config['GOOGLE_API_KEY'] = providers['gemini'].get('api_key')
            
            # 兼容旧的LLM配置格式
            if 'llm' in config:
                llm = config['llm']
                flat_config['OPENAI_API_KEY'] = llm.get('api_key')
            
            # 安全配置
            if 'security' in config:
                security = config['security']
                flat_config['SECRET_KEY'] = security.get('secret_key', "your-secret-key-here")
                flat_config['ALGORITHM'] = security.get('algorithm', "HS256")
                flat_config['ACCESS_TOKEN_EXPIRE_MINUTES'] = security.get('access_token_expire_minutes', 30)
            
            # 日志配置
            if 'logging' in config:
                logging = config['logging']
                flat_config['LOG_LEVEL'] = logging.get('level', "INFO")
            
            # Celery 配置
            if 'celery' in config:
                celery = config['celery']
                flat_config['CELERY_BROKER_URL'] = celery.get('broker_url', "redis://localhost:6379/1")
                flat_config['CELERY_RESULT_BACKEND'] = celery.get('result_backend', "redis://localhost:6379/2")
            
            print(f"✅ 成功从 YAML 配置文件加载配置: {config_file}")
            return flat_config
            
        except Exception as e:
            print(f"❌ 加载 YAML 配置文件失败: {e}")
            return {}
    
    def get_llm_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        获取指定LLM提供商的配置
        """
        return self.LLM_PROVIDERS.get(provider, {})
    
    def is_provider_configured(self, provider: str) -> bool:
        """
        检查指定提供商是否已配置
        """
        provider_config = self.get_llm_provider_config(provider)
        
        if provider == "openai":
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip()
        elif provider == "anthropic":
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip()
        elif provider == "gemini":
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip()
        elif provider == "azure":
            api_key = provider_config.get("api_key", "")
            endpoint = provider_config.get("endpoint", "")
            return api_key and api_key.strip() and endpoint and endpoint.strip()
        elif provider == "ollama":
            base_url = provider_config.get("base_url", "")
            return base_url and base_url.strip()
        
        return False
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """
        解析 CORS 源列表
        """
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS_ORIGINS must be a string or list")
    
    @validator("MCP_SERVERS", pre=True)
    def assemble_mcp_servers(cls, v):
        """
        解析 MCP 服务器列表
        """
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("MCP_SERVERS must be a string or list")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局设置实例
settings = Settings() 