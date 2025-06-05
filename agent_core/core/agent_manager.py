"""
AI Agent 管理器
负责调用大模型生成内容并调用工具服务
"""

import asyncio
from typing import Dict, Any, Optional
import httpx
from loguru import logger
import openai
import shutil
import tempfile
import zipfile
from pathlib import Path
import requests

# 导入各种LLM客户端
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic库未安装，无法使用Claude模型")

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenAI库未安装，无法使用Gemini模型")

from .config import settings


class AgentManager:
    """
    AI Agent 管理器
    负责任务分发、工作流管理和结果处理
    """
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.mcp_clients: Dict[str, str] = {}
        
        # 多个LLM客户端
        self.llm_clients = {}
        self.llm_config = None
        self.current_provider = None
        
        # 添加状态记录
        self.llm_status = {
            "configured": False,
            "current_provider": None,
            "current_model": None,
            "provider_configs": {},
            "last_updated": None
        }
    
    async def initialize(self) -> None:
        """
        初始化 Agent 管理器
        """
        try:
            logger.info("初始化 AI Agent 管理器...")
            
            # 打印配置状态
            settings.print_config_status()
            
            # 从后端获取LLM配置
            await self._load_llm_config()
            
            # 初始化 MCP 服务连接
            for service_name, config in settings.MCP_SERVICES_CONFIG.items():
                if config.get("enabled", True):
                    url = f"http://{config['host']}:{config['port']}"
                    self.mcp_clients[service_name] = url
                    logger.info(f"注册 MCP 服务: {service_name} -> {url}")
            
            self.running = True
            logger.info("AI Agent 管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化 Agent 管理器失败: {e}")
            raise e
    
    async def shutdown(self) -> None:
        """
        关闭 Agent 管理器
        """
        logger.info("关闭 AI Agent 管理器...")
        self.running = False
        
        # 清理资源
        self.tasks.clear()
        self.mcp_clients.clear()
        self.llm_clients.clear()
        
        logger.info("AI Agent 管理器已关闭")
    
    def _prepare_ucas_resources(self, temp_dir: Path) -> Dict[str, str]:
        """
        准备UCAS风格的资源文件
        
        Args:
            temp_dir: 临时目录路径
            
        Returns:
            Dict[str, str]: 资源文件映射 {文件名: 相对路径}
        """
        try:
            # UCAS图片资源目录
            path = Path("PPTStyle/ucas/images")
            
            ucas_images_dir = None
            if path.exists():
                ucas_images_dir = path
            
            # 创建images子目录
            images_dir = temp_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # 复制所有图片文件
            resource_map = {}
            for image_file in ucas_images_dir.glob("*"):
                if image_file.is_file() and image_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    dest_file = images_dir / image_file.name
                    shutil.copy2(image_file, dest_file)
                    resource_map[image_file.name] = f"images/{image_file.name}"
                    logger.info(f"复制UCAS资源文件: {image_file.name}")
            
            logger.info(f"成功准备{len(resource_map)}个UCAS资源文件")
            return resource_map
            
        except Exception as e:
            logger.error(f"准备UCAS资源文件失败: {e}")
            return {}
    
    async def _load_llm_config(self) -> bool:
        """
        从后端加载LLM配置
        """
        try:
            response = requests.get(f"{settings.BACKEND_URL}/api/config/llm", timeout=10)
            
            if response.status_code == 200:
                config_data = response.json()
                
                self.llm_status = {
                    'source': 'backend',
                    'default_provider': config_data.get('current_provider', config_data.get('default_llm_provider', 'anthropic')),
                    'providers': {}
                }
                
                providers = config_data.get('provider_configs', config_data.get('llm_providers', {}))
                
                for provider_name, provider_config in providers.items():
                    api_key = provider_config.get('api_key', '')
                    model = provider_config.get('model', '')
                    
                    self.llm_status['providers'][provider_name] = {
                        'configured': bool(api_key),
                        'model': model,
                        'api_key_set': bool(api_key)
                    }
                    
                    if provider_name == 'anthropic' and api_key:
                        self._init_anthropic_client(provider_config)
                    elif provider_name in ['gpt', 'openai'] and api_key:
                        self._init_openai_client(provider_config)
                    elif provider_name == 'gemini' and api_key:
                        self._init_gemini_client(provider_config)
                    elif provider_name == 'deepseek' and api_key:
                        self._init_deepseek_client(provider_config)
                
                default_provider = config_data.get('current_provider', config_data.get('default_llm_provider', 'anthropic'))
                if default_provider in providers and default_provider in self.llm_clients:
                    self.current_provider = default_provider
                    self.llm_config = providers[default_provider]
                else:
                    for provider_name in self.llm_clients.keys():
                        if provider_name in providers:
                            self.current_provider = provider_name
                            self.llm_config = providers[provider_name]
                            break
                
                return True
                
        except requests.exceptions.RequestException as e:
            return await self._fallback_to_local_config()
        except Exception as e:
            logger.error(f"加载LLM配置时发生错误: {e}")
            return await self._fallback_to_local_config()
    
    async def _fallback_to_local_config(self) -> bool:
        """
        回退到本地配置
        """
        try:
            self.llm_status = {
                'source': 'local',
                'default_provider': settings.DEFAULT_LLM_PROVIDER,
                'providers': {}
            }
            
            providers_config = settings.config.get('llm_providers', {})
            
            for provider_name, provider_config in providers_config.items():
                api_key = provider_config.get('api_key', '')
                model = provider_config.get('model', '')
                
                self.llm_status['providers'][provider_name] = {
                    'configured': bool(api_key),
                    'model': model,
                    'api_key_set': bool(api_key)
                }
                
                if provider_name == 'anthropic' and api_key:
                    self._init_anthropic_client(provider_config)
                elif provider_name in ['gpt', 'openai'] and api_key:
                    self._init_openai_client(provider_config)
                elif provider_name == 'gemini' and api_key:
                    self._init_gemini_client(provider_config)
                elif provider_name == 'deepseek' and api_key:
                    self._init_deepseek_client(provider_config)
            
            default_provider = settings.DEFAULT_LLM_PROVIDER
            if default_provider in providers_config and default_provider in self.llm_clients:
                self.current_provider = default_provider
                self.llm_config = providers_config[default_provider]
            else:
                for provider_name in self.llm_clients.keys():
                    if provider_name in providers_config:
                        self.current_provider = provider_name
                        self.llm_config = providers_config[provider_name]
                        break
            
            return True
            
        except Exception as e:
            logger.error(f"使用本地配置失败: {e}")
            return False
    
    def get_llm_status(self) -> Dict[str, Any]:
        """
        获取当前LLM配置状态
        """
        # 检查当前提供商是否配置完成
        is_configured = (
            self.current_provider and 
            self.llm_config and 
            self.llm_config.get("api_key", "").strip() != ""
        )
        
        if is_configured:
            return {
                "configured": True,
                "provider": self.current_provider,
                "model": self.llm_config.get("model", "gpt-4"),
                "base_url": self.llm_config.get("base_url"),
                "source": self.llm_status.get('source', 'unknown'),
                "available_providers": list(self.llm_status.get('providers', {}).keys()),
                "status": self.llm_status
            }
        else:
            return {
                "configured": False,
                "provider": self.current_provider,
                "model": None,
                "base_url": None,
                "source": self.llm_status.get('source', 'unknown'),
                "available_providers": list(self.llm_status.get('providers', {}).keys()),
                "status": self.llm_status
            }
    
    async def _call_llm(self, messages: list, **kwargs) -> str:
        """
        统一的LLM调用接口
        """
        if not self.current_provider or self.current_provider not in self.llm_clients:
            raise Exception("LLM服务未配置或初始化失败。请在系统设置中配置LLM服务，或检查后端服务是否正常运行。")
        
        provider = self.current_provider
        client = self.llm_clients[provider]
        
        try:
            if provider in ["openai", "gpt", "azure", "ollama", "deepseek"]:
                return await self._call_openai_compatible(client, messages, **kwargs)
            elif provider == "anthropic":
                return await self._call_anthropic(client, messages, **kwargs)
            elif provider == "gemini":
                return await self._call_gemini(client, messages, **kwargs)
            else:
                raise Exception(f"不支持的LLM提供商: {provider}")
                
        except Exception as e:
            logger.error(f"调用{provider} LLM失败: {e}")
            raise e
    
    async def _call_openai_compatible(self, client, messages: list, **kwargs) -> str:
        """调用OpenAI兼容的API"""
        model = self.llm_config.get("model", "gpt-4")
        max_tokens = kwargs.get("max_tokens", self.llm_config.get("max_tokens", 4000))
        temperature = kwargs.get("temperature", self.llm_config.get("temperature", 0.7))
        
        # 对于Azure，使用deployment_name作为模型名
        if self.current_provider == "azure":
            model = self.llm_config.get("deployment_name", model)
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()
    
    async def _call_anthropic(self, client, messages: list, **kwargs) -> str:
        """调用Anthropic API"""
        model = self.llm_config.get("model", "claude-3-sonnet-20240229")
        max_tokens = kwargs.get("max_tokens", self.llm_config.get("max_tokens", 4000))
        temperature = kwargs.get("temperature", self.llm_config.get("temperature", 0.7))
        
        # 转换消息格式
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        try:
            # Anthropic客户端是同步的，不需要await
            if system_message:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_message,
                    messages=user_messages
                )
            else:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=user_messages
                )
            
            # 检查响应格式
            if hasattr(response, 'content') and len(response.content) > 0:
                if hasattr(response.content[0], 'text'):
                    return response.content[0].text
                else:
                    return str(response.content[0])
            else:
                logger.error(f"Anthropic API响应格式异常: {response}")
                raise Exception("Anthropic API响应格式异常")
                
        except Exception as e:
            logger.error(f"Anthropic API调用失败: {e}")
            raise e
    
    async def _call_gemini(self, client, messages: list, **kwargs) -> str:
        """调用Gemini API"""
        model = self.llm_config.get("model", "gemini-1.5-pro")
        
        # 转换消息格式为Gemini格式
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                # 系统消息作为用户消息的前缀
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System: {msg['content']}"}]
                })
            elif msg["role"] == "user":
                contents.append({
                    "role": "user", 
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        try:
            response = client.models.generate_content(
                model=f"models/{model}",
                contents=contents
            )
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            logger.error(f"Gemini API调用失败: {e}")
            raise e
    
    async def process_task(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务
        
        Args:
            task_id: 任务ID
            task_data: 任务数据
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            logger.info(f"开始处理任务: {task_id}")
            
            # 存储任务信息
            self.tasks[task_id] = {
                "status": "running",
                "data": task_data,
                "result": None,
                "error": None
            }
            
            # 立即通知后端任务开始运行
            await self._update_backend_task(task_id, "running")
            
            # 获取任务类型
            tool_type = task_data.get("tool_type", "")
            parameters = task_data.get("parameters", {})
            
            # 截断参数日志以避免过长
            params_str = str(parameters)
            if len(params_str) > 200:
                params_str = params_str[:200] + "..."
            logger.info(f"处理任务类型: {tool_type}, 参数: {params_str}")
            
            # 根据工具类型生成内容并调用相应的 MCP 服务
            result = await self._process_with_llm(tool_type, parameters)
            
            # 更新任务状态
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["result"] = result
            
            # 通知后端更新任务状态
            await self._update_backend_task(task_id, "completed", result)
            
            logger.info(f"任务处理完成: {task_id}")
            
            return {
                "status": "success",
                "message": "任务处理完成",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"处理任务失败: {task_id}, 错误: {e}")
            
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(e)
            
            # 通知后端更新任务状态
            await self._update_backend_task(task_id, "failed", None, str(e))
            
            return {
                "status": "error",
                "message": f"任务处理失败: {str(e)}"
            }
    
    async def _process_with_llm(self, tool_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用大模型处理任务并调用相应的工具服务
        """
        try:
            if tool_type in ["ppt", "ppt_generator"]:
                return await self._generate_ppt_with_llm(parameters)
            elif tool_type in ["chart", "chart_generator"]:
                return await self._call_mcp_service(tool_type, parameters)
            elif tool_type == "chart_data_generator":
                return await self._generate_chart_data_with_llm(parameters)
            elif tool_type == "scheduler":
                return await self._call_mcp_service(tool_type, parameters)
            elif tool_type in ["api-docs", "api_doc_generator"]:
                return await self._call_mcp_service(tool_type, parameters)
            else:
                raise ValueError(f"不支持的工具类型: {tool_type}")
        except Exception as e:
            logger.error(f"LLM处理失败: {e}")
            raise e
    
    async def _generate_chart_data_with_llm(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用大模型生成图表数据
        """
        user_requirement = parameters.get("user_requirement", "")
        chart_type = parameters.get("chart_type", "bar")
        title = parameters.get("title", "")
        
        if not user_requirement:
            raise Exception("用户需求描述不能为空")
        
        try:
            # 调用OpenAI API生成图表数据
            if not self.current_provider or self.current_provider not in self.llm_clients:
                raise Exception("LLM服务未配置或初始化失败。请在系统设置中配置LLM服务，或检查后端服务是否正常运行。")
            
            # 构建提示词
            prompt = self._build_chart_data_prompt(user_requirement, chart_type, title)
            
            # 使用动态获取的模型配置
            model = self.llm_config.get("model", "gpt-4") if self.llm_config else "gpt-4"
            
            response = await self._call_llm([
                {"role": "system", "content": "你是一个专业的数据分析师，擅长根据需求生成图表数据。请生成符合Chart.js格式的JSON数据。"},
                {"role": "user", "content": prompt}
            ])
            
            generated_content = response.strip()
            
            # 提取JSON数据
            chart_data = self._extract_json_data(generated_content)
            
            return {
                "status": "success",
                "generated_data": chart_data,
                "chart_type": chart_type,
                "title": title,
                "user_requirement": user_requirement
            }
            
        except Exception as e:
            logger.error(f"生成图表数据失败: {e}")
            raise Exception(f"生成图表数据失败: {e}")
    
    def _build_chart_data_prompt(self, user_requirement: str, chart_type: str, title: str) -> str:
        """
        构建图表数据生成的提示词
        """
        # 如果是mermaid类型，生成mermaid代码
        if chart_type == "mermaid":
            return f"""请根据以下需求生成Mermaid流程图代码：

用户需求：{user_requirement}
图表类型：{chart_type}
图表标题：{title}

请生成符合Mermaid语法的代码，支持以下类型：
- 流程图：graph TD 或 graph LR
- 时序图：sequenceDiagram
- 甘特图：gantt
- 类图：classDiagram

参考格式：
```
graph TD
    A[开始] --> B[处理步骤1]
    B --> C[处理步骤2]
    C --> D[结束]
```

要求：
1. **图表选择**：根据用户需求选择最合适的Mermaid图表类型
2. **节点设计**：节点名称要有意义，与用户需求密切相关
3. **逻辑清晰**：流程要逻辑清晰，符合实际业务情况
4. **语法规范**：严格遵循Mermaid语法规范，确保可正确渲染
5. **代码纯净**：只返回Mermaid代码，不包含markdown标记或其他说明

生成的Mermaid代码："""
        
        # 其他图表类型的处理
        chart_type_descriptions = {
            "bar": "柱状图，用于比较不同类别的数值",
            "line": "折线图，用于显示数据随时间的变化趋势",
            "pie": "饼图，用于显示各部分占整体的比例",
            "scatter": "散点图，用于显示两个变量之间的关系"
        }
        
        chart_desc = chart_type_descriptions.get(chart_type, "图表")
        
        if chart_type == "bar":
            example = """{
  "labels": ["类别1", "类别2", "类别3", "类别4"],
  "datasets": [{
    "label": "数据系列名称",
    "data": [10, 20, 30, 40]
  }]
}"""
        elif chart_type == "line":
            example = """{
  "labels": ["1月", "2月", "3月", "4月", "5月"],
  "datasets": [{
    "label": "数据系列名称",
    "data": [10, 25, 15, 30, 20]
  }]
}"""
        elif chart_type == "pie":
            example = """{
  "labels": ["部分A", "部分B", "部分C", "部分D"],
  "datasets": [{
    "data": [30, 25, 25, 20]
  }]
}"""
        elif chart_type == "scatter":
            example = """{
  "datasets": [{
    "label": "数据点",
    "data": [
      {"x": 10, "y": 20},
      {"x": 15, "y": 25},
      {"x": 20, "y": 30}
    ]
  }]
}"""
        else:
            example = """{
  "labels": ["项目1", "项目2", "项目3"],
  "datasets": [{
    "label": "数据",
    "data": [10, 20, 30]
  }]
}"""
        
        return f"""请根据以下需求生成{chart_desc}的数据：

用户需求：{user_requirement}
图表类型：{chart_type}
图表标题：{title}

请生成符合Chart.js格式的JSON数据，参考格式：
{example}

要求：
1. **内容相关性**：数据要符合用户需求的主题和内容，具有实际意义
2. **数据真实性**：生成合理的数据值，避免使用明显的测试数据
3. **标签准确性**：标签和数值要有意义，与用户需求密切相关
4. **格式规范性**：严格按照Chart.js的JSON格式标准
5. **可解析性**：确保JSON格式正确，可以直接被程序解析使用

生成的JSON数据："""
    
    def _extract_json_data(self, response: str) -> str:
        """从AI响应中提取JSON数据"""
        import re
        
        # 尝试提取```json...```代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # 尝试提取```...```代码块
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # 尝试提取{...}JSON对象
        json_obj_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_obj_match:
            return json_obj_match.group(0).strip()
        
        # 如果都没找到，返回原始响应
        return response.strip()
    
    async def _generate_ppt_with_llm(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用大模型生成PPT的LaTeX内容
        """
        content = parameters.get("content", "")
        title = parameters.get("title", "演示文稿")
        theme = parameters.get("theme", "academic")
        language = parameters.get("language", "zh-CN")
        input_type = parameters.get("input_type", "text_description")
        
        # 如果是LaTeX项目，直接调用PPT服务处理
        if input_type == "latex_project":
            return await self._handle_latex_project(parameters)
        
        # 如果有自定义提示词，使用自定义提示词，否则构建默认提示词
        prompt = parameters.get("prompt")
        if not prompt:
            prompt = self._build_prompt_by_input_type(input_type, content, title, theme, language, parameters)

        try:
            # 调用OpenAI API生成内容
            if not self.current_provider or self.current_provider not in self.llm_clients:
                raise Exception("LLM服务未配置或初始化失败。请在系统设置中配置LLM服务，或检查后端服务是否正常运行。")
            
            # 使用动态获取的模型配置
            model = self.llm_config.get("model", "gpt-4") if self.llm_config else "gpt-4"
            
            response = await self._call_llm([
                {"role": "system", "content": "你是一个专业的LaTeX Beamer演示文稿生成专家。请生成高质量的LaTeX代码。重要：不要创造任何图片文件名，除非用户明确提供了图片文件。"},
                {"role": "user", "content": prompt}
            ])
            latex_content = response.strip()
            
            # 提取LaTeX代码块
            latex_content = self._extract_latex_code(latex_content)
            
            # 调用PPT服务编译LaTeX为PDF
            try:
                use_ucas_style = parameters.get("use_ucas_style", False)
                ppt_result = await self._call_ppt_service(latex_content, title, use_ucas_style)
                
                # 合并结果
                return {
                    "status": "success",
                    "latex_content": latex_content,
                    "title": title,
                    "theme": theme,
                    "input_type": input_type,
                    "pdf_path": ppt_result.get("pdf_path"),
                    "success": ppt_result.get("success", True),
                    "use_ucas_style": use_ucas_style
                }
            except Exception as e:
                logger.warning(f"PDF编译失败，但LaTeX生成成功: {e}")
                # 即使PDF编译失败，也返回LaTeX内容
                return {
                    "status": "success",
                    "latex_content": latex_content,
                    "title": title,
                    "theme": theme,
                    "input_type": input_type,
                    "pdf_compilation_error": str(e)
                }
            
        except Exception as e:
            logger.error(f"生成PPT失败: {e}")
            raise Exception(f"生成PPT失败: {e}")
    
    def _extract_latex_code(self, response: str) -> str:
        """从AI响应中提取LaTeX代码"""
        import re
        
        # 尝试提取```latex...```代码块
        latex_match = re.search(r'```latex\s*(.*?)\s*```', response, re.DOTALL)
        if latex_match:
            return latex_match.group(1).strip()
        
        # 尝试提取```...```代码块
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # 如果没有代码块，查找\documentclass开始的内容
        doc_match = re.search(r'\\documentclass.*', response, re.DOTALL)
        if doc_match:
            return doc_match.group(0).strip()
        
        # 如果都没找到，返回原始响应
        return response.strip()
    
    async def _handle_latex_project(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理LaTeX项目转换任务
        """
        try:
            uploaded_file_path = parameters.get("uploaded_file_path")
            main_tex_filename = parameters.get("main_tex_filename", "main.tex")
            title = parameters.get("title", "演示文稿")
            theme = parameters.get("theme", "academic")
            language = parameters.get("language", "zh-CN")
            
            if not uploaded_file_path:
                raise Exception("未提供上传的文件路径")
            
            # 调用PPT服务处理LaTeX项目
            service_url = self.mcp_clients.get("ppt_generator")
            if not service_url:
                raise Exception("PPT生成器服务不可用")
            
            # 读取上传的文件
            import os
            from pathlib import Path
            
            # 构建完整的文件路径
            from pathlib import Path
            
            # uploaded_file_path 可能是相对路径（如 "./uploads/file.zip" 或 "uploads\file.zip"）或绝对路径
            # 统一处理路径分隔符
            normalized_path = uploaded_file_path.replace("\\", "/")
            
            if normalized_path.startswith("./uploads/"):
                # 相对路径，需要拼接后端目录
                file_name = normalized_path.replace("./uploads/", "")
                full_file_path = Path("../backend/uploads") / file_name
            elif normalized_path.startswith("uploads/"):
                # 相对路径，需要拼接后端目录
                file_name = normalized_path.replace("uploads/", "")
                full_file_path = Path("../backend/uploads") / file_name
            else:
                # 假设是完整路径或文件名
                full_file_path = Path(uploaded_file_path)
                if not full_file_path.is_absolute():
                    # 如果不是绝对路径，假设是文件名
                    full_file_path = Path("../backend/uploads") / uploaded_file_path
            
            if not full_file_path.exists():
                raise Exception(f"上传的文件不存在: {full_file_path}")
            
            # 第一步：先读取LaTeX文件内容
            logger.info(f"开始读取LaTeX项目文件内容: {main_tex_filename}")
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    with open(full_file_path, 'rb') as f:
                        files = {'archive_file': (uploaded_file_path, f, 'application/octet-stream')}
                        data = {'main_tex_filename': main_tex_filename}
                        
                        response = await client.post(
                            f"{service_url}/extract_tex_content",
                            files=files,
                            data=data
                        )
                        response.raise_for_status()
                        extract_result = response.json()
                        
                        if not extract_result.get("success"):
                            raise Exception(f"提取LaTeX内容失败: {extract_result.get('error', '未知错误')}")
                        
                        latex_content = extract_result.get("content", "")
                        if not latex_content.strip():
                            raise Exception("提取的LaTeX内容为空")
                        
                        logger.info(f"成功提取LaTeX内容，长度: {len(latex_content)} 字符")
                        
            except httpx.RequestError as e:
                logger.error(f"提取LaTeX内容失败 - 网络错误: {e}")
                raise Exception(f"无法连接到PPT生成器服务: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"提取LaTeX内容失败 - HTTP错误: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
                raise Exception(f"PPT生成器服务返回错误 {e.response.status_code}: {e.response.text}")
            
            # 第二步：调用大模型生成Beamer代码
            
            if not self.current_provider or self.current_provider not in self.llm_clients:
                raise Exception("LLM服务未配置或初始化失败。请在系统设置中配置LLM服务，或检查后端服务是否正常运行。")
            
            # 构建LaTeX项目转换的提示词
            prompt = self._build_prompt_by_input_type("latex_project", latex_content, title, theme, language, parameters)
            
            # 使用动态获取的模型配置
            model = self.llm_config.get("model", "gpt-4") if self.llm_config else "gpt-4"
            
            try:
                response = await self._call_llm([
                    {"role": "system", "content": "你是一个专业的LaTeX Beamer演示文稿生成专家。请将学术论文的LaTeX代码转换为高质量的Beamer演示文稿代码。重要：严格禁止创造任何新的图片文件名，只能使用原始代码中已存在的\\includegraphics引用。如果原文没有图片，就不要添加图片。"},
                    {"role": "user", "content": prompt}
                ])
                beamer_content = response.strip()
                
                # 提取LaTeX代码块
                beamer_content = self._extract_latex_code(beamer_content)
                logger.info(f"大模型生成Beamer代码成功，长度: {len(beamer_content)} 字符")
                
            except Exception as e:
                logger.error(f"大模型生成Beamer代码失败: {e}")
                raise Exception(f"大模型生成Beamer代码失败: {e}")
            
            # 第三步：使用生成的Beamer代码和原项目资源编译PDF
            logger.info("开始编译Beamer代码为PDF...")
            try:
                # 检查是否使用UCAS风格
                use_ucas_style = parameters.get("use_ucas_style", False)
                
                if use_ucas_style:
                    # 如果使用UCAS风格，需要将UCAS资源文件与原项目文件合并
                    logger.info("使用UCAS风格，准备合并资源文件...")
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        
                        # 准备UCAS资源文件
                        resource_map = self._prepare_ucas_resources(temp_path)
                        
                        if resource_map:
                            # 解压原始项目文件
                            original_extract_path = temp_path / "original"
                            original_extract_path.mkdir()
                            
                            import zipfile
                            with zipfile.ZipFile(full_file_path, 'r') as zip_ref:
                                zip_ref.extractall(original_extract_path)
                            
                            # 创建合并后的压缩包
                            merged_zip_path = temp_path / "merged_project.zip"
                            
                            with zipfile.ZipFile(merged_zip_path, 'w') as zipf:
                                # 添加AI生成的Beamer文件
                                zipf.writestr("main.tex", beamer_content)
                                
                                # 添加原始项目文件（除了主tex文件）
                                for file_path in original_extract_path.rglob('*'):
                                    if file_path.is_file():
                                        relative_path = str(file_path.relative_to(original_extract_path))
                                        if relative_path != main_tex_filename:  # 跳过原始主tex文件
                                            zipf.write(file_path, relative_path)
                                            logger.debug(f"添加原始项目文件: {relative_path}")
                                
                                # 添加UCAS资源文件
                                for filename, relative_path in resource_map.items():
                                    file_path = temp_path / relative_path
                                    if file_path.exists():
                                        zipf.write(file_path, relative_path)
                                        logger.info(f"添加UCAS资源文件: {relative_path}")
                            
                            # 使用合并后的压缩包
                            async with httpx.AsyncClient(timeout=300.0) as client:
                                with open(merged_zip_path, 'rb') as f:
                                    files = {'archive_file': ('merged_project.zip', f, 'application/zip')}
                                    data = {
                                        'beamer_content': beamer_content,
                                        'title': title,
                                        'main_tex_filename': 'main.tex'
                                    }
                                    
                                    response = await client.post(
                                        f"{service_url}/generate_beamer_from_project",
                                        files=files,
                                        data=data
                                    )
                                    response.raise_for_status()
                                    result = response.json()
                        else:
                            logger.warning("UCAS资源文件准备失败，使用原始项目文件")
                            # 回退到原始方式
                            async with httpx.AsyncClient(timeout=300.0) as client:
                                with open(full_file_path, 'rb') as f:
                                    files = {'archive_file': (uploaded_file_path, f, 'application/octet-stream')}
                                    data = {
                                        'beamer_content': beamer_content,
                                        'title': title,
                                        'main_tex_filename': main_tex_filename
                                    }
                                    
                                    response = await client.post(
                                        f"{service_url}/generate_beamer_from_project",
                                        files=files,
                                        data=data
                                    )
                                    response.raise_for_status()
                                    result = response.json()
                else:
                    # 普通模式，直接使用原始项目文件
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        with open(full_file_path, 'rb') as f:
                            files = {'archive_file': (uploaded_file_path, f, 'application/octet-stream')}
                            data = {
                                'beamer_content': beamer_content,
                                'title': title,
                                'main_tex_filename': main_tex_filename
                            }
                            
                            response = await client.post(
                                f"{service_url}/generate_beamer_from_project",
                                files=files,
                                data=data
                            )
                            response.raise_for_status()
                            result = response.json()
                            
                            if not result.get("success"):
                                raise Exception(f"编译Beamer PDF失败: {result.get('error', '未知错误')}")
                            
                            logger.info("LaTeX项目转Beamer成功完成")
                            
                            return {
                                "status": "success",
                                "latex_content": beamer_content,
                                "pdf_path": result.get("pdf_path"),
                                "title": title,
                                "conversion_type": "latex_to_beamer",
                                "main_file": main_tex_filename,
                                "success": True,
                                "theme": theme,
                                "input_type": "latex_project",
                                "use_ucas_style": use_ucas_style
                            }
                        
            except httpx.RequestError as e:
                logger.error(f"编译Beamer PDF失败 - 网络错误: {e}")
                raise Exception(f"无法连接到PPT生成器服务: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"编译Beamer PDF失败 - HTTP错误: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
                raise Exception(f"PPT生成器服务返回错误 {e.response.status_code}: {e.response.text}")
            except Exception as e:
                logger.error(f"编译Beamer PDF失败: {e}")
                raise Exception(f"编译Beamer PDF失败: {e}")
            
        except Exception as e:
            logger.error(f"处理LaTeX项目失败: {e}")
            raise Exception(f"处理LaTeX项目失败: {e}")
    
    def _build_prompt_by_input_type(self, input_type: str, content: str, title: str, theme: str, language: str, parameters: Dict[str, Any] = None) -> str:
        """
        根据输入类型构建不同的提示词，支持更多样式参数
        """
        if parameters is None:
            parameters = {}
        
        # 获取样式参数
        slides_count = parameters.get("slides_count", 10)
        color_scheme = parameters.get("color_scheme", "blue")
        include_outline = parameters.get("include_outline", True)
        include_references = parameters.get("include_references", True)
        font_size = parameters.get("font_size", "medium")
        use_ucas_style = parameters.get("use_ucas_style", False)
        
        # 主题设置映射
        if use_ucas_style:
            # UCAS风格使用特殊的主题设置
            theme_settings = {
                "academic": "\\usetheme{Madrid}\\usecolortheme{default}",
                "business": "\\usetheme{CambridgeUS}\\usecolortheme{default}",
                "modern": "\\usetheme{Madrid}\\usecolortheme{default}",
                "creative": "\\usetheme{Madrid}\\usecolortheme{default}",
                "minimal": "\\usetheme{Madrid}\\usecolortheme{default}"
                        }
        else:
            theme_settings = {
                "academic": "\\usetheme{Madrid}\\usecolortheme{default}",
                "business": "\\usetheme{CambridgeUS}\\usecolortheme{beaver}",
                "modern": "\\usetheme{metropolis}",
                "creative": "\\usetheme{Berlin}\\usecolortheme{seahorse}",
                "minimal": "\\usetheme{default}"
            }
        
        # 配色方案映射
        if use_ucas_style:
            # UCAS风格使用中科院大学的配色
            color_settings = {
                "blue": "\\definecolor{ucasblue}{RGB}{0,82,155}\\setbeamercolor{structure}{fg=ucasblue}",
                "green": "\\definecolor{ucasgreen}{RGB}{0,128,0}\\setbeamercolor{structure}{fg=ucasgreen}",
                "red": "\\definecolor{ucasred}{RGB}{196,18,48}\\setbeamercolor{structure}{fg=ucasred}",
                "purple": "\\definecolor{ucaspurple}{RGB}{102,45,145}\\setbeamercolor{structure}{fg=ucaspurple}",
                "orange": "\\definecolor{ucasorange}{RGB}{255,102,0}\\setbeamercolor{structure}{fg=ucasorange}"
            }
        else:
            color_settings = {
                "blue": "\\usecolortheme{default}",
                "green": "\\usecolortheme{seahorse}",
                "red": "\\usecolortheme{rose}",
                "purple": "\\usecolortheme{orchid}",
                "orange": "\\usecolortheme{whale}"
            }
        
        theme_code = theme_settings.get(theme, theme_settings["academic"])
        color_code = color_settings.get(color_scheme, color_settings["blue"])
        
        # 字体大小设置
        font_size_code = {
            "small": "\\tiny",
            "medium": "\\normalsize", 
            "large": "\\large"
        }.get(font_size, "\\normalsize")

        # 准备模板中的可选部分
        outline_frame = "\\begin{frame}{目录}\\tableofcontents\\end{frame}" if include_outline else ""
        references_frame = "\\begin{frame}{参考文献}\\end{frame}" if include_references else ""

        # 构建特殊要求和模板
        if use_ucas_style:
            ucas_requirements = f"""
要求：
1. 主题风格：UCAS中国科学院大学风格 ({theme_code})
2. 配色方案：{color_scheme} (UCAS定制配色)
3. 语言：{language}
4. 标题：{title}
5. 目标幻灯片数量：约{slides_count}张
6. 字体大小：{font_size}
7. 包含完整的LaTeX文档结构
8. 支持中文显示（使用xeCJK包）
9. 内容要结构清晰，格式美观
10. 生成的代码必须是完整可编译的LaTeX Beamer文档
11. 使用UCAS中国科学院大学的视觉元素和标识
12. 在适当位置引用UCAS相关图片资源
{"13. 包含目录页" if include_outline else ""}
{"14. 包含参考文献页" if include_references else ""}

请使用以下UCAS风格模板结构：
```latex
\\documentclass[aspectratio=169]{{beamer}}
\\usepackage{{xeCJK}}
\\usepackage{{graphicx}}
\\usepackage{{tikz}}
\\setCJKmainfont{{SimSun}}
{theme_code}
{color_code}

% UCAS标识和背景设置（条件性包含）
\\IfFileExists{{images/logo.png}}{{
  \\setbeamertemplate{{background}}{{
    \\begin{{tikzpicture}}[remember picture,overlay]
      \\node[at=(current page.south east),anchor=south east,inner sep=0pt] {{
        \\includegraphics[width=0.15\\paperwidth]{{images/logo.png}}
      }};
    \\end{{tikzpicture}}
  }}
}}{{}}

% 标题页背景（条件性包含）
\\setbeamertemplate{{title page}}{{
  \\IfFileExists{{images/bg.png}}{{
    \\begin{{tikzpicture}}[remember picture,overlay]
      \\node[at=(current page.center),opacity=0.1] {{
        \\includegraphics[width=0.8\\paperwidth]{{images/bg.png}}
      }};
    \\end{{tikzpicture}}
  }}{{}}
  \\vfill
  \\begin{{center}}
    \\IfFileExists{{images/logo1.png}}{{
      \\includegraphics[width=0.2\\paperwidth]{{images/logo1.png}}\\\\[1em]
    }}{{}}
    \\usebeamerfont{{title}}\\inserttitle\\\\[0.5em]
    \\usebeamerfont{{subtitle}}\\insertsubtitle\\\\[1em]
    \\usebeamerfont{{author}}\\insertauthor\\\\[0.5em]
    \\usebeamerfont{{institute}}中国科学院大学\\\\[0.5em]
    \\usebeamerfont{{date}}\\insertdate
  \\end{{center}}
  \\vfill
}}

\\title{{{title}}}
\\author{{AI生成}}
\\date{{\\today}}

\\begin{{document}}

\\frame{{\\titlepage}}

{outline_frame}

% 在这里生成内容幻灯片...
% 注意：可以在适当位置使用以下图片资源：
% - images/logo.png (UCAS主标识)
% - images/logo1.png (UCAS标识变体)
% - images/bg.png (背景图片)
% - images/bg1.jpg 到 images/bg6.jpg (各种背景图片)
% - images/photo.png (示例照片)

{references_frame}

\\end{{document}}
```
"""
            base_requirements = ucas_requirements
        else:
            base_requirements = f"""
要求：
1. 主题风格：{theme} ({theme_code})
2. 配色方案：{color_scheme} ({color_code})
3. 语言：{language}
4. 标题：{title}
5. 目标幻灯片数量：约{slides_count}张
6. 字体大小：{font_size}
7. 包含完整的LaTeX文档结构
8. 支持中文显示（使用xeCJK包）
9. 内容要结构清晰，格式美观
10. 生成的代码必须是完整可编译的LaTeX Beamer文档
{"11. 包含目录页" if include_outline else ""}
{"12. 包含参考文献页" if include_references else ""}

请使用以下模板结构：
```latex
\\documentclass[aspectratio=169]{{beamer}}
\\usepackage{{xeCJK}}
\\setCJKmainfont{{SimSun}}
{theme_code}
{color_code}

\\title{{{title}}}
\\author{{AI生成}}
\\date{{\\today}}

\\begin{{document}}

\\frame{{\\titlepage}}

{outline_frame}

% 在这里生成内容幻灯片...

{references_frame}

\\end{{document}}
```
"""

        if input_type == "text_description":
            return f"""请根据以下文字描述生成一个完整的LaTeX Beamer演示文稿代码。

{base_requirements}

文字描述：
{content}

请分析描述内容，提取关键信息，组织成清晰的幻灯片结构。

要求：
1. **内容组织**：合理分配内容到约{slides_count}张幻灯片，每张幻灯片内容适中
2. **结构清晰**：使用适当的标题和子标题，逻辑层次分明
3. **格式规范**：支持Markdown格式的内容转换为LaTeX格式
4. **视觉效果**：适当使用列表、强调等格式增强可读性
5. **完整性**：生成完整可编译的LaTeX Beamer文档

生成完整的LaTeX代码："""

        elif input_type == "document_content":
            return f"""请根据以下文档内容生成一个完整的LaTeX Beamer演示文稿代码。

{base_requirements}

文档内容：
{content}

请分析文档内容，提取核心观点和关键信息，重新组织成适合演示的幻灯片结构。

要求：
1. **内容提炼**：将文档内容合理分割为约{slides_count}张幻灯片，突出重点
2. **信息层次**：突出重点内容和关键信息，次要信息适当简化
3. **逻辑结构**：保持清晰的逻辑结构，便于听众理解
4. **演示适配**：内容适合口头演示，避免过于详细的文字描述
5. **视觉平衡**：每张幻灯片信息量适中，视觉效果良好

生成完整的LaTeX代码："""

        elif input_type == "latex_project":
            return f"""请将以下LaTeX学术论文内容转换为LaTeX Beamer演示文稿格式。

⚠️ 重要警告：严格禁止创造任何新的图片文件名！只能使用原始代码中已存在的\\includegraphics引用！

{base_requirements}

LaTeX源码：
{content}

请分析论文结构，提取以下关键部分并组织成学术演示文稿：
- 标题和作者信息
- 研究背景和动机
- 主要贡献和方法
- 实验结果
- 结论和未来工作

特别注意：
1. **图片引用规则**：
   - 严格禁止创造任何新的图片文件名
   - 只能使用原始LaTeX代码中已经存在的\\includegraphics引用
   - 如果原文没有图片引用，则不要添加任何图片
   - 绝对不要使用描述性的图片名称如"Results on multiple objects.png"、"Visualization results.png"等
2. **引用格式**：保持原有的引用格式（如 \\cite{{}}、\\ref{{}}、\\label{{}}等）
3. **内容分割**：将内容合理分割为约{slides_count}张幻灯片，每张幻灯片内容适中
4. **数学公式**：保留重要的数学公式和表格，确保公式编号正确
5. **文档结构**：生成完整可编译的LaTeX Beamer文档，包含必要的包引用
6. **中文支持**：确保中文内容能正确显示
7. **图片处理策略**：如果需要展示实验结果或图表，使用文字描述替代，不要添加图片引用

生成完整的LaTeX Beamer代码："""

        else:
            # 默认处理
            return f"""请根据以下内容生成一个完整的LaTeX Beamer演示文稿代码。

{base_requirements}

内容：
{content}

要求：
1. **内容分析**：分析提供的内容，提取关键信息和主要观点
2. **结构设计**：设计清晰的演示结构，包含约{slides_count}张幻灯片
3. **格式规范**：使用标准的LaTeX Beamer格式和语法
4. **完整性**：生成完整可编译的LaTeX文档
5. **可读性**：确保内容易于理解和演示

生成完整的LaTeX代码："""
    
    async def _call_ppt_service(self, latex_content: str, title: str, use_ucas_style: bool = False) -> Dict[str, Any]:
        """
        调用PPT生成器服务编译LaTeX
        """
        service_url = self.mcp_clients.get("ppt_generator")
        if not service_url:
            raise Exception("PPT生成器服务不可用")
        
        try:
            # 如果使用UCAS风格，需要准备资源文件
            if use_ucas_style:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    # 准备UCAS资源文件
                    resource_map = self._prepare_ucas_resources(temp_path)
                    
                    if resource_map:
                        # 创建包含资源文件的压缩包
                        zip_path = temp_path / "ucas_resources.zip"
                        
                        logger.info(f"创建UCAS资源压缩包: {zip_path}")
                        logger.info(f"资源文件映射: {resource_map}")
                        
                        with zipfile.ZipFile(zip_path, 'w') as zipf:
                            # 添加LaTeX文件
                            zipf.writestr("main.tex", latex_content)
                            logger.info("已添加main.tex到压缩包")
                            
                            # 添加所有资源文件
                            for filename, relative_path in resource_map.items():
                                file_path = temp_path / relative_path
                                if file_path.exists():
                                    zipf.write(file_path, relative_path)
                                    logger.info(f"已添加资源文件到压缩包: {relative_path}")
                                else:
                                    logger.warning(f"资源文件不存在: {file_path}")
                        
                        # 验证压缩包内容
                        with zipfile.ZipFile(zip_path, 'r') as zipf:
                            zip_contents = zipf.namelist()
                            logger.info(f"压缩包内容: {zip_contents}")
                        
                        # 使用带资源文件的接口
                        async with httpx.AsyncClient(timeout=600.0) as client:
                            with open(zip_path, 'rb') as f:
                                files = {'archive_file': (zip_path.name, f, 'application/zip')}
                                data = {
                                    'beamer_content': latex_content,
                                    'title': title,
                                    'main_tex_filename': 'main.tex'
                                }
                                
                                response = await client.post(
                                    f"{service_url}/generate_beamer_from_project",
                                    files=files,
                                    data=data
                                )
                                response.raise_for_status()
                                return response.json()
                    else:
                        logger.warning("UCAS资源文件准备失败，使用普通模式")
            
            # 普通模式或UCAS资源准备失败时的处理
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"{service_url}/generate_ppt",
                    json={
                        "latex_content": latex_content,
                        "title": title
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"调用PPT服务失败 - 网络错误: {e}")
            raise Exception(f"无法连接到PPT生成器服务: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"调用PPT服务失败 - HTTP错误: {e.response.status_code}")
            logger.error(f"响应内容: {e.response.text}")
            raise Exception(f"PPT生成器服务返回错误 {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"调用PPT服务失败 - 未知错误: {e}")
            raise Exception(f"调用PPT服务失败: {e}")
    
    async def _call_mcp_service(self, tool_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 服务
        """
        # 工具类型映射
        service_mapping = {
            "ppt": "ppt_generator",
            "ppt_generator": "ppt_generator",
            "chart": "chart_generator", 
            "chart_generator": "chart_generator",
            "scheduler": "schedule_reminder",
            "api-docs": "api_doc_generator",
            "api_doc_generator": "api_doc_generator"
        }
        
        service_name = service_mapping.get(tool_type)
        if not service_name or service_name not in self.mcp_clients:
            raise ValueError(f"不支持的工具类型: {tool_type}")
        
        service_url = self.mcp_clients[service_name]
        
        logger.info(f"调用 MCP 服务: {service_name} at {service_url}")
        
        try:
            # 根据服务类型调用相应的端点
            async with httpx.AsyncClient(timeout=30.0) as client:
                if tool_type in ["chart", "chart_generator"]:
                    # 调用图表生成器服务
                    response = await client.post(
                        f"{service_url}/generate_chart",
                        json=parameters
                    )
                elif tool_type == "scheduler":
                    # 调用日程提醒服务
                    response = await client.post(
                        f"{service_url}/create_schedule",
                        json=parameters
                    )
                elif tool_type in ["api-docs", "api_doc_generator"]:
                    # 调用 API 文档生成器服务
                    response = await client.post(
                        f"{service_url}/generate_docs",
                        json=parameters
                    )
                else:
                    raise ValueError(f"未知的工具类型: {tool_type}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"MCP 服务调用成功: {service_name}")
                return result
                
        except httpx.RequestError as e:
            logger.error(f"调用 MCP 服务失败 - 网络错误: {e}")
            raise Exception(f"无法连接到 {service_name} 服务: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"调用 MCP 服务失败 - HTTP错误: {e.response.status_code}")
            raise Exception(f"{service_name} 服务返回错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"调用 MCP 服务失败: {e}")
            raise Exception(f"调用 {service_name} 服务失败: {e}")
    
    async def _update_backend_task(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        更新后端任务状态
        """
        try:
            async with httpx.AsyncClient() as client:
                update_data = {"status": status}
                if result:
                    update_data["result"] = result
                if error_message:
                    update_data["error_message"] = error_message
                
                response = await client.put(
                    f"{settings.BACKEND_URL}/api/tasks/{task_id}",
                    json=update_data,
                    timeout=10.0
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.warning(f"更新后端任务状态失败: {e}")
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务
        """
        try:
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = "cancelled"
                await self._update_backend_task(task_id, "cancelled")
                logger.info(f"任务已取消: {task_id}")
                return {"status": "success", "message": "任务已取消"}
            else:
                return {"status": "error", "message": "任务不存在"}
                
        except Exception as e:
            logger.error(f"取消任务失败: {task_id}, 错误: {e}")
            raise e
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        """
        try:
            if task_id in self.tasks:
                return self.tasks[task_id]
            else:
                return {"status": "not_found", "message": "任务不存在"}
                
        except Exception as e:
            logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
            raise e
    
    async def reload_llm_config(self) -> Dict[str, Any]:
        """
        重新加载LLM配置
        """
        try:
            settings.reload_config()
            success = await self._load_llm_config()
            
            if success and self.current_provider:
                model = self.llm_config.get("model", "gpt-4") if self.llm_config else "gpt-4"
                source = self.llm_status.get('source', 'unknown')
                return {
                    "status": "success", 
                    "message": f"LLM配置重新加载成功，当前模型: {model} (来源: {source})",
                    "config": {
                        "provider": self.current_provider,
                        "model": model,
                        "configured": True,
                        "source": source,
                        "status": self.llm_status
                    }
                }
            else:
                return {
                    "status": "warning", 
                    "message": "LLM配置重新加载完成，但未能成功初始化客户端",
                    "config": {
                        "configured": False,
                        "status": self.llm_status
                    }
                }
                
        except Exception as e:
            logger.error(f"重新加载LLM配置失败: {e}")
            return {"status": "error", "message": f"重新加载LLM配置失败: {e}"}

    def _init_anthropic_client(self, config: Dict[str, Any]) -> bool:
        """初始化Anthropic客户端"""
        try:
            if not ANTHROPIC_AVAILABLE:
                return False
            
            api_key = config.get("api_key")
            if not api_key:
                return False
            
            # 使用代理配置
            proxy_url = "http://127.0.0.1:7890"
            try:
                from anthropic import DefaultHttpxClient
                import httpx
                client = anthropic.Anthropic(
                    api_key=api_key,
                    http_client=DefaultHttpxClient(
                        proxy=proxy_url,
                        transport=httpx.HTTPTransport(local_address="0.0.0.0")
                    )
                )
            except ImportError:
                # 如果httpx不可用，使用默认客户端
                client = anthropic.Anthropic(api_key=api_key)
            
            self.llm_clients["anthropic"] = client
            return True
            
        except Exception as e:
            logger.error(f"初始化Anthropic客户端失败: {e}")
            return False

    def _init_openai_client(self, config: Dict[str, Any]) -> bool:
        """初始化OpenAI兼容客户端（支持OpenAI/GPT/DeepSeek等）"""
        try:
            api_key = config.get("api_key")
            base_url = config.get("base_url", "https://api.openai.com/v1")
            
            if not api_key:
                return False
            
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            if "openai.com" in base_url:
                self.llm_clients["openai"] = client
                self.llm_clients["gpt"] = client
            elif "deepseek.com" in base_url:
                self.llm_clients["deepseek"] = client
            else:
                provider_name = config.get("provider", "openai")
                self.llm_clients[provider_name] = client
            
            return True
            
        except Exception as e:
            logger.error(f"初始化OpenAI兼容客户端失败: {e}")
            return False

    def _init_deepseek_client(self, config: Dict[str, Any]) -> bool:
        """初始化DeepSeek客户端"""
        try:
            api_key = config.get("api_key")
            base_url = config.get("base_url", "https://api.deepseek.com")
            
            if not api_key:
                return False
            
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            self.llm_clients["deepseek"] = client
            return True
            
        except Exception as e:
            logger.error(f"初始化DeepSeek客户端失败: {e}")
            return False

    def _init_gemini_client(self, config: Dict[str, Any]) -> bool:
        """初始化Gemini客户端"""
        try:
            if not GEMINI_AVAILABLE:
                return False
            
            api_key = config.get("api_key")
            if not api_key:
                return False
            
            client = genai.Client(api_key=api_key)
            self.llm_clients["gemini"] = client
            return True
            
        except Exception as e:
            logger.error(f"初始化Gemini客户端失败: {e}")
            return False

 