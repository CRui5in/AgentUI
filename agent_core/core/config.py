"""
AI Agent 核心配置模块
"""

import os
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path


class Settings:
    """Agent 核心设置"""
    
    def __init__(self):
        self.config_file = Path(__file__).parent.parent / "config.yaml"
        self.config = self._load_config()
        
        # 基础配置
        self.DEBUG: bool = self.config.get("server", {}).get("debug", True)
        self.LOG_LEVEL: str = self.config.get("logging", {}).get("level", "INFO")
        
        # 服务配置
        server_config = self.config.get("server", {})
        self.AGENT_HOST: str = server_config.get("host", "0.0.0.0")
        self.AGENT_PORT: int = server_config.get("port", 8001)
        
        # 后端服务连接
        self.BACKEND_URL: str = self.config.get("backend", {}).get("url", "http://localhost:8000")
        
        # 统一处理LLM配置格式
        if 'provider_configs' in self.config:
            # 新格式：多提供商配置
            self.LLM_PROVIDERS: Dict[str, Any] = self.config.get("provider_configs", {})
            self.DEFAULT_LLM_PROVIDER: str = self.config.get("current_provider", "openai")
        else:
            # 兼容旧格式
            self.LLM_PROVIDERS: Dict[str, Any] = self.config.get("llm_providers", {})
            self.DEFAULT_LLM_PROVIDER: str = self.config.get("default_llm_provider", "openai")
        
        # 向后兼容的单一配置（从默认提供商获取）
        default_provider_config = self.LLM_PROVIDERS.get(self.DEFAULT_LLM_PROVIDER, {})
        self.OPENAI_API_KEY: str = default_provider_config.get("api_key", "")
        self.OPENAI_MODEL: str = default_provider_config.get("model", "gpt-4")
        self.OPENAI_BASE_URL: Optional[str] = default_provider_config.get("base_url")
        
        # 其他提供商的快捷访问
        anthropic_config = self.LLM_PROVIDERS.get("anthropic", {})
        self.ANTHROPIC_API_KEY: str = anthropic_config.get("api_key", "")
        
        gemini_config = self.LLM_PROVIDERS.get("gemini", {})
        self.GOOGLE_API_KEY: str = gemini_config.get("api_key", "")
        
        # MCP 服务配置
        self.MCP_SERVICES_CONFIG: Dict[str, Any] = self.config.get("mcp_services", {
            "ppt_generator": {"host": "localhost", "port": 8002, "enabled": True},
            "chart_generator": {"host": "localhost", "port": 8003, "enabled": True},
            "schedule_reminder": {"host": "localhost", "port": 8004, "enabled": True},
            "api_doc_generator": {"host": "localhost", "port": 8005, "enabled": True}
        })
        
        # 安全配置
        security_config = self.config.get("security", {})
        self.SECRET_KEY: str = security_config.get("secret_key", "your-secret-key-here")
        self.ALLOWED_HOSTS: str = ",".join(security_config.get("allowed_hosts", ["localhost", "127.0.0.1"]))
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件，优先使用YAML，如果不存在则尝试.env
        """
        # 首先尝试加载YAML配置
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    print(f"✅ 成功加载YAML配置文件: {self.config_file}")
                    
                    # 直接返回YAML配置，不做格式转换
                    return config or {}
        except Exception as e:
            print(f"❌ 加载YAML配置文件失败: {e}")
        
        # 如果YAML不存在，尝试从环境变量加载
        print("⚠️  YAML配置文件不存在，尝试从环境变量加载...")
        return self._load_from_env()
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        从环境变量加载配置（兼容.env文件）
        """
        # 尝试加载.env文件
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                print(f"✅ 成功加载.env文件: {env_file}")
            except ImportError:
                print("⚠️  需要安装python-dotenv包来支持.env文件")
            except Exception as e:
                print(f"❌ 加载.env文件失败: {e}")
        
        # 从环境变量构建配置
        return {
            "llm_providers": {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                    "base_url": os.getenv("OPENAI_BASE_URL"),
                    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
                },
                "anthropic": {
                    "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                    "temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
                    "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "4000"))
                },
                "gemini": {
                    "api_key": os.getenv("GOOGLE_API_KEY", ""),
                    "model": os.getenv("GEMINI_MODEL", "gemini-pro"),
                    "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
                    "max_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "4000"))
                },
                "azure": {
                    "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
                    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                    "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                    "temperature": float(os.getenv("AZURE_TEMPERATURE", "0.7")),
                    "max_tokens": int(os.getenv("AZURE_MAX_TOKENS", "4000"))
                },
                "ollama": {
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "model": os.getenv("OLLAMA_MODEL", "llama2"),
                    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                    "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "4000"))
                }
            },
            "default_llm_provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
            "server": {
                "host": os.getenv("AGENT_HOST", "0.0.0.0"),
                "port": int(os.getenv("AGENT_PORT", "8001")),
                "debug": os.getenv("DEBUG", "true").lower() == "true"
            },
            "backend": {
                "url": os.getenv("BACKEND_URL", "http://localhost:8000")
            },
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO")
            },
            "security": {
                "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
                "allowed_hosts": os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
            }
        }
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """将 ALLOWED_HOSTS 字符串转换为列表"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    def is_openai_configured(self) -> bool:
        """
        检查OpenAI是否已配置
        """
        return (self.OPENAI_API_KEY and 
                self.OPENAI_API_KEY != "your_openai_api_key_here" and
                len(self.OPENAI_API_KEY.strip()) > 0)
    
    def is_provider_configured(self, provider: str) -> bool:
        """
        检查指定提供商是否已配置
        """
        provider_config = self.LLM_PROVIDERS.get(provider, {})
        
        if provider in ["openai", "gpt"]:
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip() and api_key not in ["", "your_openai_api_key_here"]
        elif provider == "anthropic":
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip() and api_key not in ["", "your_anthropic_api_key_here"]
        elif provider == "gemini":
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip() and api_key not in ["", "your_google_api_key_here"]
        elif provider == "deepseek":
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip() and api_key not in ["", "your_deepseek_api_key_here"]
        elif provider == "azure":
            api_key = provider_config.get("api_key", "")
            endpoint = provider_config.get("endpoint", "")
            return (api_key and api_key.strip() and api_key not in ["", "your_azure_api_key_here"] and
                    endpoint and endpoint.strip())
        elif provider == "ollama":
            base_url = provider_config.get("base_url", "")
            return base_url and base_url.strip()
        
        return False
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        获取指定提供商的配置
        """
        return self.LLM_PROVIDERS.get(provider, {})
    
    def reload_config(self):
        """
        重新加载配置
        """
        old_config = self.config.copy()
        self.__init__()
        
        # 检查关键配置是否发生变化
        old_openai_key = old_config.get("llm_providers", {}).get("openai", {}).get("api_key")
        new_openai_key = self.LLM_PROVIDERS.get("openai", {}).get("api_key")
        if old_openai_key != new_openai_key:
            print("🔄 检测到OpenAI API密钥变化，配置已重新加载")
        
        old_provider = old_config.get("default_llm_provider")
        if old_provider != self.DEFAULT_LLM_PROVIDER:
            print(f"🔄 检测到默认LLM提供商变化: {old_provider} -> {self.DEFAULT_LLM_PROVIDER}")
        
        self.print_config_status()
    
    def print_config_status(self):
        """
        打印配置状态
        """
        print("\n=== Agent核心配置状态 ===")
        print(f"默认LLM提供商: {self.DEFAULT_LLM_PROVIDER}")
        
        # 显示所有配置的提供商
        for provider in ["openai", "gpt", "anthropic", "gemini", "azure", "ollama", "deepseek"]:
            status = "✅ 已配置" if self.is_provider_configured(provider) else "❌ 未配置"
            print(f"{provider.upper()}: {status}")
        
        print(f"服务端口: {self.AGENT_PORT}")
        print(f"后端地址: {self.BACKEND_URL}")
        print(f"调试模式: {'开启' if self.DEBUG else '关闭'}")
        print("注意: 系统将优先使用后端系统设置中的LLM配置")
        print("========================\n")


# 创建全局设置实例
settings = Settings() 