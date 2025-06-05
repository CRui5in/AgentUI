"""
工具相关 API 端点
提供工具类型查询和配置功能
"""

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from loguru import logger

# 创建路由器
router = APIRouter()


@router.get("/types", response_model=List[str])
async def get_tool_types() -> List[str]:
    """
    获取可用的工具类型列表
    """
    try:
        tool_types = [
            "ppt_generator",
            "chart_generator", 
            "scheduler",
            "api_doc_generator"
        ]
        return tool_types
    
    except Exception as e:
        logger.error(f"获取工具类型失败: {e}")
        raise HTTPException(status_code=500, detail="获取工具类型失败")


@router.get("/{tool_type}/config", response_model=Dict[str, Any])
async def get_tool_config(tool_type: str) -> Dict[str, Any]:
    """
    获取指定工具的配置信息
    """
    try:
        # 工具配置映射
        tool_configs = {
            "ppt_generator": {
                "name": "PPT 生成器",
                "description": "基于 LaTeX Beamer 的演示文稿生成工具",
                "parameters": {
                    "content": {"type": "string", "required": True, "description": "演示文稿内容"},
                    "theme": {"type": "string", "required": False, "default": "default", "options": ["default", "modern", "academic"]},
                    "language": {"type": "string", "required": False, "default": "zh-CN", "options": ["zh-CN", "en-US"]},
                    "title": {"type": "string", "required": False, "description": "演示文稿标题"}
                }
            },
            "chart_generator": {
                "name": "图表生成器",
                "description": "数据可视化图表生成工具",
                "parameters": {
                    "data": {"type": "string", "required": True, "description": "JSON 格式的数据"},
                    "chart_type": {"type": "string", "required": True, "options": ["line", "bar", "pie", "scatter", "histogram"]},
                    "title": {"type": "string", "required": False, "description": "图表标题"},
                    "x_column": {"type": "string", "required": False, "description": "X 轴列名"},
                    "y_column": {"type": "string", "required": False, "description": "Y 轴列名"}
                }
            },
            "scheduler": {
                "name": "日程管理器",
                "description": "智能日程安排和提醒工具",
                "parameters": {
                    "title": {"type": "string", "required": True, "description": "事件标题"},
                    "description": {"type": "string", "required": False, "description": "事件描述"},
                    "start_time": {"type": "datetime", "required": True, "description": "开始时间"},
                    "end_time": {"type": "datetime", "required": False, "description": "结束时间"},
                    "reminder_minutes": {"type": "integer", "required": False, "description": "提前提醒分钟数"}
                }
            },
            "api_doc_generator": {
                "name": "API 文档生成器",
                "description": "自动生成 API 文档工具",
                "parameters": {
                    "source_path": {"type": "string", "required": True, "description": "源代码路径"},
                    "output_format": {"type": "string", "required": True, "options": ["markdown", "html"]},
                    "include_private": {"type": "boolean", "required": False, "default": False, "description": "是否包含私有方法"}
                }
            }
        }
        
        if tool_type not in tool_configs:
            raise HTTPException(status_code=404, detail="工具类型不存在")
        
        return tool_configs[tool_type]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工具配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取工具配置失败") 