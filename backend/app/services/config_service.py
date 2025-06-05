"""
配置服务
负责管理应用的各种配置信息
"""

import json
import os
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
import aiofiles
import httpx
import yaml
from loguru import logger

from app.core.config import settings

# 导入各提供商的官方SDK
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import anthropic
    from anthropic import DefaultHttpxClient
except ImportError:
    anthropic = None

try:
    from google import genai
except ImportError:
    genai = None


class ConfigService:
    """配置服务类"""
    
    def __init__(self):
        self.config_dir = Path("./configs")
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.llm_config_file = self.config_dir / "llm_config.json"
        self.database_config_file = self.config_dir / "database_config.json"
        self.service_config_file = self.config_dir / "service_config.json"
        self.app_config_file = self.config_dir / "app_config.json"
        self.config_path = Path(__file__).parent.parent.parent / "config.yaml"
        logger.debug(f"后端配置文件路径: {self.config_path.absolute()}")
        self._config_cache = None
    
    async def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self._config_cache is None:
            await self._load_config()
        return self._config_cache or {}
    
    async def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_cache = yaml.safe_load(f) or {}
            else:
                self._config_cache = {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self._config_cache = {}
    
    async def update_config(self, config: Dict[str, Any]) -> bool:
        """更新配置"""
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            # 更新缓存
            self._config_cache = config
            logger.info("配置更新成功")
            return True
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    async def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        try:
            # 直接从YAML配置文件读取
            config_path = Path("../agent_core/config.yaml")
            if not config_path.exists():
                # 如果Agent配置不存在，尝试后端配置
                config_path = Path("config.yaml")
            
            if config_path.exists():
                async with aiofiles.open(config_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    yaml_config = yaml.safe_load(content) or {}
                
                # 从YAML格式转换为新的多提供商格式
                if 'llm_providers' in yaml_config:
                    current_provider = yaml_config.get('default_llm_provider', 'openai')
                    provider_configs = yaml_config.get('llm_providers', {})
                    
                    config = {
                        'current_provider': current_provider,
                        'provider_configs': provider_configs
                    }
                    
                    logger.info(f"从YAML配置文件加载LLM配置: {config_path}")
                    return config
                else:
                    logger.warning(f"YAML配置文件中未找到llm_providers配置: {config_path}")
            
            # 返回包含所有提供商的默认配置
            default_config = {
                "current_provider": "openai",
                "provider_configs": {
                    "openai": {
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "model": "",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    "gpt": {
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    "anthropic": {
                        "api_key": "",
                        "base_url": "https://api.anthropic.com",
                        "model": "claude-3-sonnet-20240229",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    "gemini": {
                        "api_key": "",
                        "base_url": "https://generativelanguage.googleapis.com",
                        "model": "gemini-1.5-pro",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    "azure": {
                        "api_key": "",
                        "endpoint": "",
                        "api_version": "2024-02-15-preview",
                        "deployment_name": "",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    "ollama": {
                        "api_key": "",
                        "base_url": "http://localhost:11434",
                        "model": "llama2",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    "deepseek": {
                        "api_key": "",
                        "base_url": "https://api.deepseek.com",
                        "model": "deepseek-chat",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    }
                }
            }
            logger.info("使用默认LLM配置")
            return default_config
        except Exception as e:
            logger.error(f"获取LLM配置失败: {e}")
            raise e
    
    async def save_llm_config(self, config: Dict[str, Any]) -> None:
        """保存LLM配置到YAML文件"""
        try:
            # 同时更新后端的config.yaml文件
            await self._update_backend_config_yaml(config)
            
            # 同时更新Agent核心的config.yaml文件
            await self._update_agent_config_yaml(config)
            
            logger.info("所有LLM YAML配置文件更新完成")
            
        except Exception as e:
            logger.error(f"保存LLM配置失败: {e}")
            raise e
    
    async def save_provider_config(self, provider: str, provider_config: Dict[str, Any]) -> None:
        """保存单个提供商的配置"""
        try:
            # 获取现有的完整配置
            full_config = await self.get_llm_config()
            
            # 更新指定提供商的配置
            if 'provider_configs' not in full_config:
                full_config['provider_configs'] = {}
            
            full_config['provider_configs'][provider] = provider_config
            
            # 保存完整配置
            await self.save_llm_config(full_config)
            logger.info(f"提供商 {provider} 配置保存成功")
            
        except Exception as e:
            logger.error(f"保存提供商 {provider} 配置失败: {e}")
            raise e
    
    async def set_current_provider(self, provider: str) -> None:
        """设置当前使用的提供商"""
        try:
            # 获取现有配置
            config = await self.get_llm_config()
            
            # 更新当前提供商
            config['current_provider'] = provider
            
            # 保存配置
            await self.save_llm_config(config)
            logger.info(f"当前LLM提供商设置为: {provider}")
            
        except Exception as e:
            logger.error(f"设置当前提供商失败: {e}")
            raise e
    
    async def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        try:
            if self.database_config_file.exists():
                async with aiofiles.open(self.database_config_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                return {
                    "type": "sqlite",
                    "host": "localhost",
                    "port": 5432,
                    "database": "ai_app.db",
                    "username": "",
                    "password": ""
                }
        except Exception as e:
            logger.error(f"获取数据库配置失败: {e}")
            raise e
    
    async def save_database_config(self, config: Dict[str, Any]) -> None:
        """保存数据库配置"""
        try:
            async with aiofiles.open(self.database_config_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(config, indent=2, ensure_ascii=False))
            logger.info("数据库配置保存成功")
        except Exception as e:
            logger.error(f"保存数据库配置失败: {e}")
            raise e
    
    async def get_service_config(self) -> Dict[str, Any]:
        """获取服务配置"""
        try:
            if self.service_config_file.exists():
                async with aiofiles.open(self.service_config_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                return {
                    "backend_url": "http://localhost:8000",
                    "agent_url": "http://localhost:8001",
                    "ppt_service_url": "http://localhost:8002",
                    "chart_service_url": "http://localhost:8003",
                    "timeout": 30000
                }
        except Exception as e:
            logger.error(f"获取服务配置失败: {e}")
            raise e
    
    async def save_service_config(self, config: Dict[str, Any]) -> None:
        """保存服务配置"""
        try:
            async with aiofiles.open(self.service_config_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(config, indent=2, ensure_ascii=False))
            logger.info("服务配置保存成功")
        except Exception as e:
            logger.error(f"保存服务配置失败: {e}")
            raise e
    
    async def get_app_config(self) -> Dict[str, Any]:
        """获取应用配置"""
        try:
            if self.app_config_file.exists():
                async with aiofiles.open(self.app_config_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                return {
                    "theme": "light",
                    "language": "zh-CN",
                    "auto_save": True,
                    "notifications": True,
                    "debug_mode": False
                }
        except Exception as e:
            logger.error(f"获取应用配置失败: {e}")
            raise e
    
    async def save_app_config(self, config: Dict[str, Any]) -> None:
        """保存应用配置"""
        try:
            async with aiofiles.open(self.app_config_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(config, indent=2, ensure_ascii=False))
            logger.info("应用配置保存成功")
        except Exception as e:
            logger.error(f"保存应用配置失败: {e}")
            raise e
    
    async def test_llm_connection(self, config: Dict[str, Any]) -> bool:
        """测试LLM连接"""
        try:
            provider = config.get("provider", "openai")
            api_key = config.get("api_key", "")
            base_url = config.get("base_url", "")
            model = config.get("model", "gpt-4")
            
            if not api_key:
                logger.warning("API密钥为空")
                return False
            
            # 根据提供商类型进行不同的连接测试
            if provider in ["openai", "gpt", "deepseek"]:
                return await self._test_openai_compatible_connection(api_key, base_url, model)
            elif provider == "anthropic":
                return await self._test_anthropic_connection(api_key)
            elif provider == "gemini":
                return await self._test_gemini_connection(api_key)
            elif provider == "azure":
                endpoint = config.get("endpoint", "")
                api_version = config.get("api_version", "2024-02-15-preview")
                deployment_name = config.get("deployment_name", "")
                return await self._test_azure_connection(api_key, endpoint, api_version, deployment_name)
            elif provider == "ollama":
                base_url = base_url or "http://localhost:11434"
                return await self._test_ollama_connection(base_url)
            else:
                logger.warning(f"不支持的提供商: {provider}")
                return False
                    
        except Exception as e:
            logger.error(f"测试LLM连接失败: {e}")
            return False
    
    async def _test_openai_compatible_connection(self, api_key: str, base_url: str, model: str) -> bool:
        """测试OpenAI兼容API连接"""
        try:
            logger.info(f"测试OpenAI兼容API连接: {base_url}")
            
            # 使用OpenAI SDK进行对话测试
            if OpenAI:
                import asyncio
                
                def sync_test_connection():
                    client = OpenAI(
                        api_key=api_key,
                        base_url=base_url or "https://api.openai.com/v1",
                        timeout=10.0  # 设置10秒超时
                    )
                    
                    response = client.chat.completions.create(
                        model=model or "gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant"},
                            {"role": "user", "content": "Hello"}
                        ],
                        max_tokens=10,
                        temperature=0
                    )
                    
                    if response.choices and response.choices[0].message.content:
                        return True
                    else:
                        return False
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_test_connection),
                    timeout=15.0
                )
                
                if result:
                    logger.info(f"OpenAI兼容API对话测试成功: {base_url}")
                    return True
                else:
                    logger.error("OpenAI兼容API返回空响应")
                    return False
            else:
                logger.error("OpenAI库未安装")
                return False
                    
        except asyncio.TimeoutError:
            logger.error(f"OpenAI兼容API连接测试超时: {base_url}")
            return False
        except Exception as e:
            logger.error(f"OpenAI兼容API连接测试失败: {e}")
            return False
    
    async def _test_anthropic_connection(self, api_key: str) -> bool:
        """测试Anthropic API连接"""
        try:
            logger.info("测试Anthropic API连接")
            
            # 使用Anthropic SDK进行对话测试
            if anthropic:
                import asyncio
                
                def sync_test_connection():
                    # 使用代理配置
                    proxy_url = "http://127.0.0.1:7890"
                    client = anthropic.Anthropic(
                        api_key=api_key, 
                        http_client=DefaultHttpxClient(
                            proxy=proxy_url, 
                            transport=httpx.HTTPTransport(local_address="0.0.0.0")
                        )
                    )
                    
                    message = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=10,
                        messages=[
                            {"role": "user", "content": "Hello, Claude"}
                        ]
                    )
                    
                    if message.content and len(message.content) > 0:
                        return True
                    else:
                        return False
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_test_connection),
                    timeout=15.0
                )
                
                if result:
                    logger.info("Anthropic API对话测试成功")
                    return True
                else:
                    logger.error("Anthropic API返回空响应")
                    return False
            else:
                logger.error("Anthropic库未安装")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Anthropic API连接测试超时")
            return False
        except Exception as e:
            logger.error(f"Anthropic API连接测试失败: {e}")
            return False
    
    async def _test_gemini_connection(self, api_key: str) -> bool:
        """测试Gemini API连接"""
        try:
            logger.info("测试Gemini API连接")
            
            # 使用Google GenAI SDK进行对话测试
            try:
                import asyncio
                
                def sync_test_connection():
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    
                    response = client.models.generate_content(
                        model="gemini-1.5-flash", 
                        contents="Hello"
                    )
                    
                    if response.text and response.text.strip():
                        return True
                    else:
                        return False
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_test_connection),
                    timeout=15.0
                )
                
                if result:
                    logger.info("Gemini API对话测试成功")
                    return True
                else:
                    logger.error("Gemini API返回空响应")
                    return False
                    
            except ImportError:
                logger.error("Google GenAI库未安装")
                return False
                    
        except asyncio.TimeoutError:
            logger.error("Gemini API连接测试超时")
            return False
        except Exception as e:
            logger.error(f"Gemini API连接测试失败: {e}")
            return False
    
    async def _test_azure_connection(self, api_key: str, endpoint: str, api_version: str, deployment_name: str) -> bool:
        """测试Azure OpenAI连接"""
        try:
            if not endpoint or not deployment_name:
                logger.warning("Azure配置不完整")
                return False
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "api-key": api_key,
                    "Content-Type": "application/json"
                }
                
                # 使用chat completions endpoint测试连接
                url = f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
                test_data = {
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
                
                response = await client.post(url, headers=headers, json=test_data)
                
                if response.status_code in [200, 400]:  # 400也算连接成功，只是参数问题
                    logger.info("Azure OpenAI连接测试成功")
                    return True
                else:
                    logger.error(f"Azure OpenAI连接测试失败: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Azure OpenAI连接测试失败: {e}")
            return False
    
    async def _test_ollama_connection(self, base_url: str) -> bool:
        """测试Ollama连接"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                
                if response.status_code == 200:
                    logger.info("Ollama连接测试成功")
                    return True
                else:
                    logger.error(f"Ollama连接测试失败: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Ollama连接测试失败: {e}")
            return False
    
    async def test_database_connection(self, config: Dict[str, Any]) -> bool:
        """测试数据库连接"""
        try:
            db_type = config.get("type", "sqlite")
            
            if db_type == "sqlite":
                # SQLite 只需要检查文件是否可以创建/访问
                db_path = config.get("database", "ai_app.db")
                try:
                    # 尝试创建或访问数据库文件
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    conn.close()
                    logger.info("SQLite数据库连接测试成功")
                    return True
                except Exception as e:
                    logger.error(f"SQLite连接测试失败: {e}")
                    return False
            else:
                # PostgreSQL/MySQL 连接测试
                logger.warning(f"暂不支持 {db_type} 数据库连接测试")
                return True  # 暂时返回True
                
        except Exception as e:
            logger.error(f"测试数据库连接失败: {e}")
            return False
    
    async def test_service_connection(self, config: Dict[str, Any]) -> bool:
        """测试服务连接"""
        try:
            services = [
                ("后端服务", config.get("backend_url", "")),
                ("Agent服务", config.get("agent_url", "")),
                ("PPT服务", config.get("ppt_service_url", "")),
                ("图表服务", config.get("chart_service_url", ""))
            ]
            
            timeout = config.get("timeout", 30000) / 1000  # 转换为秒
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                all_success = True
                
                for service_name, url in services:
                    if not url:
                        continue
                        
                    try:
                        # 尝试访问健康检查端点
                        health_endpoints = ["/health", "/", "/api/health"]
                        service_success = False
                        
                        for endpoint in health_endpoints:
                            try:
                                response = await client.get(f"{url}{endpoint}")
                                if response.status_code < 500:  # 4xx也算连接成功
                                    logger.info(f"{service_name} 连接成功: {url}")
                                    service_success = True
                                    break
                            except:
                                continue
                        
                        if not service_success:
                            logger.warning(f"{service_name} 连接失败: {url}")
                            all_success = False
                            
                    except Exception as e:
                        logger.error(f"测试 {service_name} 连接失败: {e}")
                        all_success = False
                
                return all_success
                
        except Exception as e:
            logger.error(f"测试服务连接失败: {e}")
            return False
    
    async def _update_backend_config_yaml(self, llm_config: Dict[str, Any]) -> None:
        """更新后端的config.yaml文件"""
        try:
            # 读取现有的后端配置
            backend_config = {}
            if self.config_path.exists():
                async with aiofiles.open(self.config_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    backend_config = yaml.safe_load(content) or {}
            
            # 确保llm_providers节点存在
            if 'llm_providers' not in backend_config:
                backend_config['llm_providers'] = {}
            
            # 如果是新格式配置，保存所有提供商
            if 'provider_configs' in llm_config:
                for provider, provider_config in llm_config['provider_configs'].items():
                    if provider not in backend_config['llm_providers']:
                        backend_config['llm_providers'][provider] = {}
                    backend_config['llm_providers'][provider].update(provider_config)
                
                # 设置当前默认提供商
                current_provider = llm_config.get('current_provider', 'openai')
                backend_config['default_llm_provider'] = current_provider
                
                # 保持向后兼容的llm字段（从当前提供商配置提取）
                current_config = llm_config['provider_configs'].get(current_provider, {})
            else:
                # 向后兼容：处理旧格式
                provider = llm_config.get('provider', 'openai')
                if provider not in backend_config['llm_providers']:
                    backend_config['llm_providers'][provider] = {}
                
                # 更新提供商配置，排除provider字段
                provider_config = {k: v for k, v in llm_config.items() if k != 'provider'}
                backend_config['llm_providers'][provider].update(provider_config)
                backend_config['default_llm_provider'] = provider
                
                # 保持向后兼容的llm字段
                current_config = llm_config
            
            # 更新向后兼容的llm字段
            if 'llm' not in backend_config:
                backend_config['llm'] = {}
            backend_config['llm']['provider'] = current_config.get('provider', backend_config.get('default_llm_provider', 'openai'))
            backend_config['llm']['api_key'] = current_config.get('api_key', '')
            backend_config['llm']['base_url'] = current_config.get('base_url', 'https://api.openai.com/v1')
            backend_config['llm']['model'] = current_config.get('model', 'gpt-4')
            backend_config['llm']['temperature'] = current_config.get('temperature', 0.7)
            backend_config['llm']['max_tokens'] = current_config.get('max_tokens', 2048)
            
            # 写回配置文件
            async with aiofiles.open(self.config_path, 'w', encoding='utf-8') as f:
                yaml_content = yaml.dump(backend_config, default_flow_style=False, allow_unicode=True, indent=2)
                await f.write(yaml_content)
            
            logger.info(f"后端配置文件更新成功: {self.config_path}")
            
        except Exception as e:
            logger.error(f"更新后端配置文件失败: {e}")
            # 不抛出异常，避免影响其他配置保存

    async def _update_agent_config_yaml(self, llm_config: Dict[str, Any]) -> None:
        """更新Agent核心的config.yaml文件"""
        try:
            # Agent配置文件路径
            agent_config_path = Path("../agent_core/config.yaml")
            logger.debug(f"Agent配置文件路径: {agent_config_path.absolute()}")
            
            # 如果文件不存在，创建默认配置
            if not agent_config_path.exists():
                logger.warning(f"Agent配置文件不存在: {agent_config_path}")
                await self._create_default_agent_config(agent_config_path, llm_config)
                return
            
            # 读取现有配置
            async with aiofiles.open(agent_config_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                config = yaml.safe_load(content) or {}
            
            # 确保llm_providers节点存在
            if 'llm_providers' not in config:
                config['llm_providers'] = {}
            
            # 如果是新格式配置，保存所有提供商
            if 'provider_configs' in llm_config:
                for provider, provider_config in llm_config['provider_configs'].items():
                    if provider not in config['llm_providers']:
                        config['llm_providers'][provider] = {}
                    config['llm_providers'][provider].update(provider_config)
                
                # 设置当前默认提供商
                current_provider = llm_config.get('current_provider', 'openai')
                config['default_llm_provider'] = current_provider
                
                # 保持向后兼容的openai字段（从当前提供商配置提取）
                current_config = llm_config['provider_configs'].get(current_provider, {})
            else:
                # 向后兼容：处理旧格式
                provider = llm_config.get('provider', 'openai')
                if provider not in config['llm_providers']:
                    config['llm_providers'][provider] = {}
                
                # 更新提供商配置，排除provider字段
                provider_config = {k: v for k, v in llm_config.items() if k != 'provider'}
                config['llm_providers'][provider].update(provider_config)
                config['default_llm_provider'] = provider
                
                # 保持向后兼容的openai字段
                current_config = llm_config
            if 'openai' not in config:
                config['openai'] = {}
            config['openai']['api_key'] = current_config.get('api_key', '')
            config['openai']['model'] = current_config.get('model', 'gpt-4')
            config['openai']['base_url'] = current_config.get('base_url', '')
            
            # 写回配置文件
            async with aiofiles.open(agent_config_path, 'w', encoding='utf-8') as f:
                yaml_content = yaml.dump(config, default_flow_style=False, allow_unicode=True, indent=2)
                await f.write(yaml_content)
            
            logger.info(f"Agent配置文件更新成功: {agent_config_path}")
            
            # 通知Agent重新加载配置
            await self._notify_agent_reload_config()
            
        except Exception as e:
            logger.error(f"更新Agent配置文件失败: {e}")
            # 不抛出异常，避免影响后端配置保存
    
    async def _create_default_agent_config(self, config_path: Path, llm_config: Dict[str, Any]) -> None:
        """创建默认的Agent配置文件"""
        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            default_config = {
                'openai': {
                    'api_key': llm_config.get('api_key', ''),
                    'model': llm_config.get('model', 'gpt-4'),
                    'base_url': llm_config.get('base_url') if llm_config.get('base_url') != 'https://api.openai.com/v1' else None
                },
                'anthropic': {
                    'api_key': 'your_anthropic_api_key_here'
                },
                'google': {
                    'api_key': 'your_google_api_key_here'
                },
                'server': {
                    'host': '0.0.0.0',
                    'port': 8001,
                    'debug': True
                },
                'backend': {
                    'url': 'http://localhost:8000'
                },
                'mcp_services': {
                    'ppt_generator': {
                        'host': 'localhost',
                        'port': 8002,
                        'enabled': True
                    },
                    'chart_generator': {
                        'host': 'localhost',
                        'port': 8003,
                        'enabled': True
                    },
                    'schedule_reminder': {
                        'host': 'localhost',
                        'port': 8004,
                        'enabled': True
                    },
                    'api_doc_generator': {
                        'host': 'localhost',
                        'port': 8005,
                        'enabled': True
                    }
                },
                'logging': {
                    'level': 'INFO',
                    'file': 'logs/agent.log'
                },
                'security': {
                    'secret_key': 'your_secret_key_here',
                    'allowed_hosts': ['localhost', '127.0.0.1']
                }
            }
            
            async with aiofiles.open(config_path, 'w', encoding='utf-8') as f:
                yaml_content = yaml.dump(default_config, default_flow_style=False, allow_unicode=True, indent=2)
                await f.write(yaml_content)
            
            logger.info(f"创建默认Agent配置文件: {config_path}")
            
        except Exception as e:
            logger.error(f"创建默认Agent配置文件失败: {e}")
    
    async def _notify_agent_reload_config(self) -> None:
        """通知Agent重新加载配置"""
        try:
            # 尝试多个可能的Agent端口
            agent_ports = [8001, 8000]  # 8001是默认端口，8000是备用
            
            for port in agent_ports:
                try:
                    agent_url = f"http://localhost:{port}"
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        response = await client.post(f"{agent_url}/api/config/llm/reload")
                        if response.status_code == 200:
                            logger.info(f"Agent配置重新加载通知发送成功 (端口: {port})")
                            return
                        else:
                            logger.debug(f"Agent端口 {port} 响应状态: {response.status_code}")
                except Exception as e:
                    logger.debug(f"尝试Agent端口 {port} 失败: {e}")
                    continue
            
            logger.warning("所有Agent端口都无法连接，配置通知失败")
            
        except Exception as e:
            logger.warning(f"通知Agent重新加载配置失败: {e}")

    async def _sync_from_agent_config(self) -> None:
        """从Agent配置文件同步LLM配置到后端"""
        try:
            # Agent配置文件路径
            agent_config_path = Path("../agent_core/config.yaml")
            
            if not agent_config_path.exists():
                return
            
            # 读取Agent配置
            async with aiofiles.open(agent_config_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                agent_config = yaml.safe_load(content) or {}
            
            # 如果Agent配置中有LLM提供商配置，同步到后端
            if 'llm_providers' in agent_config:
                current_provider = agent_config.get('default_llm_provider', 'openai')
                
                backend_config = {
                    'current_provider': current_provider,
                    'provider_configs': agent_config['llm_providers']
                }
                
                # 如果后端配置文件不存在，则从Agent配置同步
                if not self.llm_config_file.exists():
                    await self.save_llm_config(backend_config)
                    logger.info("从Agent配置同步LLM配置到后端")
                else:
                    # 如果后端配置存在，但Agent配置较新，可以选择性同步
                    logger.debug("后端配置文件已存在，使用后端配置")
                
        except Exception as e:
            logger.debug(f"从Agent配置同步失败: {e}")
            # 不抛出异常，避免影响正常配置读取

    async def reload_configs(self) -> None:
        """重新加载所有配置"""
        try:
            # 强制从Agent配置文件同步
            await self._sync_from_agent_config()
            logger.info("配置重新加载完成")
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            raise e
    
    async def get_available_models(self, provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> List[str]:
        """手动获取指定提供商的可用模型列表"""
        try:
            if provider == "gpt":
                return await self._get_gpt_models(api_key)
            elif provider == "anthropic":
                return await self._get_anthropic_models(api_key)
            elif provider == "gemini":
                return await self._get_gemini_models(api_key)
            elif provider == "deepseek":
                return await self._get_deepseek_models(api_key, base_url)
            elif provider == "ollama":
                return await self._get_ollama_models(base_url or "http://localhost:11434")
            elif provider == "azure":
                # Azure 使用部署名称，不需要获取模型列表
                return ["使用部署名称"]
            elif provider == "openai":
                # OpenAI 通用接口，支持自定义模型
                return ["自定义模型"]
            else:
                logger.warning(f"不支持的提供商: {provider}")
                return []
        except Exception as e:
            logger.error(f"获取 {provider} 模型列表失败: {e}")
            return []
    
    async def _get_gpt_models(self, api_key: Optional[str]) -> List[str]:
        """获取GPT模型列表"""
        if not api_key:
            return []
        
        try:
            # 使用OpenAI SDK
            if OpenAI:
                import asyncio
                
                def sync_get_models():
                    client = OpenAI(api_key=api_key)
                    models = client.models.list()
                    model_names = [model.id for model in models.data]
                    # 过滤出GPT相关模型
                    gpt_models = [model for model in model_names if 'gpt' in model.lower()]
                    return sorted(gpt_models)
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                models = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_get_models),
                    timeout=15.0
                )
                logger.info(f"成功获取GPT模型列表: {len(models)}个模型")
                return models
            else:
                logger.error("OpenAI库未安装")
                return []
                    
        except asyncio.TimeoutError:
            logger.error("获取GPT模型列表超时")
            return []
        except Exception as e:
            logger.error(f"获取GPT模型失败: {e}")
            return []
    
    async def _get_anthropic_models(self, api_key: Optional[str]) -> List[str]:
        """获取Anthropic模型列表"""
        if not api_key:
            return []
        
        try:
            # 使用Anthropic SDK
            if anthropic:
                import asyncio
                
                def sync_get_models():
                    proxy_url = "http://127.0.0.1:7890"
                    client = anthropic.Anthropic(api_key=api_key, http_client=DefaultHttpxClient(proxy=proxy_url, transport=httpx.HTTPTransport(local_address="0.0.0.0")))
                    models = client.models.list(limit=20)
                    model_names = [model.id for model in models.data]
                    return sorted(model_names)
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                models = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_get_models),
                    timeout=15.0
                )
                logger.info(f"成功获取Anthropic模型列表: {len(models)}个模型")
                return models
            else:
                logger.error("Anthropic库未安装")
                return []
                    
        except asyncio.TimeoutError:
            logger.error("获取Anthropic模型列表超时")
            return []
        except Exception as e:
            logger.error(f"获取Anthropic模型失败: {e}")
            return []
    
    async def _get_gemini_models(self, api_key: Optional[str]) -> List[str]:
        """获取Gemini模型列表"""
        if not api_key:
            return []
        
        try:
            # 使用Google GenAI SDK
            try:
                from google import genai
                import asyncio
                
                def sync_get_models():
                    client = genai.Client(api_key=api_key)
                    
                    models = []
                    for model in client.models.list():
                        for action in model.supported_actions:
                            if action == "generateContent":
                                # 移除models/前缀用于前端显示
                                model_name = model.name
                                if model_name.startswith("models/"):
                                    display_name = model_name.replace("models/", "")
                                else:
                                    display_name = model_name
                                models.append(display_name)
                                break
                    
                    return sorted(list(set(models)))  # 去重并排序
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                models = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_get_models),
                    timeout=15.0
                )
                logger.info(f"成功获取Gemini模型列表: {len(models)}个模型")
                return models
            except ImportError:
                logger.error("Google GenAI库未安装")
                return []
                    
        except asyncio.TimeoutError:
            logger.error("获取Gemini模型列表超时")
            return []
        except Exception as e:
            logger.error(f"获取Gemini模型失败: {e}")
            return []
    
    async def _get_deepseek_models(self, api_key: Optional[str], base_url: Optional[str]) -> List[str]:
        """获取DeepSeek模型列表"""
        if not api_key:
            return []
        
        try:
            # 使用OpenAI SDK with DeepSeek endpoint
            if OpenAI:
                import asyncio
                
                def sync_get_models():
                    client = OpenAI(
                        api_key=api_key,
                        base_url=base_url or "https://api.deepseek.com"
                    )
                    models = client.models.list()
                    model_names = [model.id for model in models.data]
                    return sorted(model_names)
                
                # 在线程池中运行同步代码，设置15秒总超时
                loop = asyncio.get_event_loop()
                models = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_get_models),
                    timeout=15.0
                )
                logger.info(f"成功获取DeepSeek模型列表: {len(models)}个模型")
                return models
            else:
                logger.error("OpenAI库未安装")
                return []
                    
        except asyncio.TimeoutError:
            logger.error("获取DeepSeek模型列表超时")
            return []
        except Exception as e:
            logger.error(f"获取DeepSeek模型失败: {e}")
            return []
    
    async def _get_ollama_models(self, base_url: str) -> List[str]:
        """获取Ollama模型列表"""
        if not httpx:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return sorted(models)
                else:
                    return []
        except asyncio.TimeoutError:
            logger.error("获取Ollama模型列表超时")
            return []
        except Exception as e:
            logger.error(f"获取Ollama模型失败: {e}")
            return [] 