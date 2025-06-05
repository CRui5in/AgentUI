"""
图表生成器 MCP 服务
使用 FastMCP 框架提供图表生成功能，支持多种图表类型和AI生成
"""

import hashlib
import os
import subprocess
import tempfile
import shutil
import json
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib import font_manager
import base64


class ChartRequest(BaseModel):
    """图表生成请求模型"""
    chart_type: str  # bar, line, pie, scatter, mermaid, flow, mindmap, etc.
    data: Optional[str] = None  # JSON数据或代码
    title: Optional[str] = None
    description: Optional[str] = None
    width: Optional[int] = 800
    height: Optional[int] = 600
    theme: Optional[str] = "default"
    color_scheme: Optional[str] = "blue"
    style_options: Optional[Dict[str, Any]] = None


class ChartAIRequest(BaseModel):
    """AI图表生成请求模型"""
    description: str  # 图表描述
    chart_type: str  # 期望的图表类型
    data_source: Optional[str] = None  # 数据来源描述
    style_preferences: Optional[Dict[str, Any]] = None


class ChartGenerator:
    """
    图表生成器类
    支持传统数据图表和AI生成的图表
    """
    
    def __init__(self):
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        
        # 设置中文字体
        self._setup_chinese_fonts()
        
        # 设置样式
        plt.style.use('default')
        sns.set_palette("husl")
    
    def _setup_chinese_fonts(self):
        """设置中文字体支持"""
        try:
            # 设置中文字体优先级列表
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 强制刷新字体缓存
            from matplotlib.font_manager import fontManager
            fontManager.addfont('C:/Windows/Fonts/msyh.ttc')  # 微软雅黑字体文件
            
            # 验证字体是否可用
            import matplotlib.font_manager as fm
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            if 'Microsoft YaHei' in available_fonts:
                logger.info("成功加载微软雅黑字体")
            else:
                logger.warning("微软雅黑字体不可用，尝试使用其他中文字体")
                
        except Exception as e:
            logger.warning(f"字体设置失败: {e}")
            # 备用方案：使用系统默认中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
    
    async def generate_chart(
        self,
        chart_type: str,
        data: Optional[str] = None,
        title: Optional[str] = None,
        width: int = 800,
        height: int = 600,
        theme: str = "default",
        color_scheme: str = "blue",
        style_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成图表
        
        Args:
            chart_type: 图表类型
            data: 图表数据或代码
            title: 图表标题
            width: 宽度
            height: 高度
            theme: 主题
            color_scheme: 配色方案
            style_options: 样式选项
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            logger.info(f"开始生成图表: type={chart_type}, title={title}")
            
            if chart_type in ['mermaid', 'flow', 'mindmap', 'sequence', 'gantt']:
                # 生成代码类图表
                if not data:
                    raise Exception("Mermaid代码不能为空")
                image_path = await self._generate_code_chart(
                    chart_type, data, title, width, height
                )
            else:
                # 生成数据图表
                if not data:
                    raise Exception("图表数据不能为空")
                image_path = await self._generate_data_chart(
                    chart_type, data, title, width, height, theme, color_scheme, style_options
                )
            
            # 获取文件名用于下载URL
            filename = image_path.name
            
            result = {
                "success": True,
                "image_path": str(image_path),
                "filename": filename,
                "download_url": f"/download/{filename}",
                "title": title,
                "chart_type": chart_type,
                "width": width,
                "height": height
            }
            
            logger.info(f"图表生成成功: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"图表生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def generate_chart_with_ai(
        self,
        description: str,
        chart_type: str,
        data_source: Optional[str] = None,
        style_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用AI生成图表（自动生成数据或代码）
        """
        try:
            logger.info(f"开始AI生成图表: {chart_type} - {description}")
            
            # 获取样式参数
            width = style_preferences.get('width', 800) if style_preferences else 800
            height = style_preferences.get('height', 600) if style_preferences else 600
            theme = style_preferences.get('theme', 'default') if style_preferences else 'default'
            color_scheme = style_preferences.get('color_scheme', 'blue') if style_preferences else 'blue'
            
            # 根据图表类型和描述生成相应的代码或数据
            if chart_type in ['mermaid', 'flow', 'mindmap', 'sequence', 'gantt']:
                # 生成图表代码
                chart_code = await self._generate_chart_code_with_ai(description, chart_type)
                image_path = await self._generate_code_chart(chart_type, chart_code, description, width, height)
            else:
                # 生成数据图表
                chart_data = await self._generate_chart_data_with_ai(description, chart_type, data_source)
                image_path = await self._generate_data_chart(chart_type, chart_data, description, width, height, theme, color_scheme)
            
            # 获取文件名用于下载URL
            filename = image_path.name
            
            result = {
                "success": True,
                "image_path": str(image_path),
                "filename": filename,
                "download_url": f"/download/{filename}",
                "title": description,
                "chart_type": chart_type,
                "ai_generated": True
            }
            
            logger.info(f"AI图表生成成功: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"AI图表生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def _generate_code_chart(
        self,
        chart_type: str,
        code: str,
        title: Optional[str] = None,
        width: int = 800,
        height: int = 600
    ) -> Path:
        """
        生成代码类图表（mermaid等）
        """
        if chart_type == 'mermaid':
            return await self._generate_mermaid_chart(code, title, width, height)
        else:
            raise Exception(f"不支持的代码图表类型: {chart_type}")
    
    async def _generate_mermaid_chart(
        self,
        mermaid_code: str,
        title: Optional[str] = None,
        width: int = 800,
        height: int = 600
    ) -> Path:
        """
        生成Mermaid图表
        """
        # 尝试多种方式查找mermaid-cli
        mmdc_cmd = None
        possible_commands = [
            'mmdc',
            'npx @mermaid-js/mermaid-cli',
            'C:\\Users\\%USERNAME%\\AppData\\Roaming\\npm\\mmdc.cmd',
            'C:\\Program Files\\nodejs\\mmdc.cmd'
        ]
        
        for cmd in possible_commands:
            try:
                # 展开环境变量
                if '%USERNAME%' in cmd:
                    import os
                    cmd = cmd.replace('%USERNAME%', os.environ.get('USERNAME', ''))
                
                # 测试命令是否可用
                if cmd.startswith('npx'):
                    test_result = subprocess.run(cmd.split() + ['--version'], 
                                               capture_output=True, text=True, timeout=10)
                else:
                    test_result = subprocess.run([cmd, '--version'], 
                                               capture_output=True, text=True, timeout=10)
                
                if test_result.returncode == 0:
                    mmdc_cmd = cmd
                    logger.info(f"找到mermaid-cli: {cmd}")
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                continue
        
        if not mmdc_cmd:
            # 如果都找不到，尝试使用npx作为最后手段
            mmdc_cmd = 'npx @mermaid-js/mermaid-cli'
            logger.warning("未找到mermaid-cli，尝试使用npx")
        
        # 生成安全的文件名
        import hashlib
        safe_filename = hashlib.md5((title or "mermaid_chart").encode('utf-8')).hexdigest()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 写入mermaid文件
            mmd_file = temp_path / f"{safe_filename}.mmd"
            with open(mmd_file, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)
            
            # 输出文件路径
            output_file = self.output_dir / f"{safe_filename}.png"
            
            # 使用mermaid-cli生成图表
            if mmdc_cmd.startswith('npx'):
                cmd = mmdc_cmd.split() + [
                    '-i', str(mmd_file),
                    '-o', str(output_file),
                    '-w', str(width),
                    '-H', str(height),
                    '--theme', 'default'
                ]
            else:
                cmd = [
                    mmdc_cmd,
                    '-i', str(mmd_file),
                    '-o', str(output_file),
                    '-w', str(width),
                    '-H', str(height),
                    '--theme', 'default'
                ]
            
            logger.info(f"执行mermaid命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Mermaid命令输出: stdout={result.stdout}, stderr={result.stderr}")
                raise Exception(f"Mermaid生成失败: {result.stderr or result.stdout or '未知错误'}")
            
            if not output_file.exists():
                raise Exception("Mermaid图表文件生成失败")
            
            return output_file
    
    async def _generate_data_chart(
        self,
        chart_type: str,
        data: str,
        title: Optional[str] = None,
        width: int = 800,
        height: int = 600,
        theme: str = "default",
        color_scheme: str = "blue",
        style_options: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        生成数据图表
        """
        try:
            
            # 解析数据
            if not data:
                raise Exception("数据不能为空")
            
            # 尝试解析JSON数据
            try:
                chart_data = json.loads(data) if isinstance(data, str) else data
            except json.JSONDecodeError:
                # 如果不是有效的JSON，可能是简单的描述，生成示例数据
                logger.warning(f"无法解析JSON数据，使用描述生成示例数据: {data}")
                chart_data = await self._generate_sample_data_from_description(data, chart_type)
            
            # 检查数据是否为字典格式
            if not isinstance(chart_data, dict):
                logger.warning(f"数据格式不正确，使用描述生成示例数据: {chart_data}")
                chart_data = await self._generate_sample_data_from_description(str(chart_data), chart_type)
            
            if not chart_data or not isinstance(chart_data, dict):
                raise Exception("解析后的数据为空或格式不正确")
            
            # 设置图表大小
            fig, ax = plt.subplots(figsize=(width/100, height/100))
            
            # 确保中文字体设置生效
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 设置颜色方案
            colors = self._get_color_palette(color_scheme)
            
            if chart_type == 'bar':
                await self._create_bar_chart(ax, chart_data, colors)
            elif chart_type == 'line':
                await self._create_line_chart(ax, chart_data, colors)
            elif chart_type == 'pie':
                await self._create_pie_chart(ax, chart_data, colors)
            elif chart_type == 'scatter':
                await self._create_scatter_chart(ax, chart_data, colors)
            else:
                raise Exception(f"不支持的图表类型: {chart_type}")
            
            # 设置标题
            if title:
                ax.set_title(title, fontsize=16, fontweight='bold', 
                           fontproperties='Microsoft YaHei')
            
            # 应用主题
            self._apply_theme(fig, ax, theme)
            
            # 保存图表
            safe_filename = hashlib.md5((title or "chart").encode('utf-8')).hexdigest()
            output_file = self.output_dir / f"{safe_filename}.png"
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            return output_file
            
        except Exception as e:
            plt.close('all')  # 确保清理
            raise e
    
    def _get_color_palette(self, color_scheme: str) -> List[str]:
        """获取配色方案"""
        palettes = {
            'blue': ['#1f77b4', '#aec7e8', '#2ca02c', '#98df8a', '#d62728'],
            'green': ['#2ca02c', '#98df8a', '#1f77b4', '#aec7e8', '#ff7f0e'],
            'red': ['#d62728', '#ff9896', '#2ca02c', '#98df8a', '#1f77b4'],
            'purple': ['#9467bd', '#c5b0d5', '#2ca02c', '#98df8a', '#d62728'],
            'orange': ['#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#1f77b4'],
            'rainbow': plt.cm.Set3.colors
        }
        return palettes.get(color_scheme, palettes['blue'])
    
    async def _create_bar_chart(self, ax, data, colors):
        """创建柱状图"""
        labels = data.get('labels', [])
        datasets = data.get('datasets', [])
        
        if not datasets:
            raise Exception("缺少数据集")
        
        x = np.arange(len(labels))
        width = 0.8 / len(datasets)
        
        for i, dataset in enumerate(datasets):
            values = dataset.get('data', [])
            label = dataset.get('label', f'数据集{i+1}')
            color = colors[i % len(colors)]
            
            ax.bar(x + i * width - width * (len(datasets) - 1) / 2, 
                  values, width, label=label, color=color)
        
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontproperties='Microsoft YaHei')
        ax.legend(prop={'family': 'Microsoft YaHei'})
    
    async def _create_line_chart(self, ax, data, colors):
        """创建折线图"""
        labels = data.get('labels', [])
        datasets = data.get('datasets', [])
        
        for i, dataset in enumerate(datasets):
            values = dataset.get('data', [])
            label = dataset.get('label', f'数据集{i+1}')
            color = colors[i % len(colors)]
            
            ax.plot(labels, values, label=label, color=color, 
                   marker='o', linewidth=2, markersize=6)
        
        # 设置x轴标签字体
        ax.set_xticklabels(ax.get_xticklabels(), fontproperties='Microsoft YaHei')
        ax.legend(prop={'family': 'Microsoft YaHei'})
    
    async def _create_pie_chart(self, ax, data, colors):
        """创建饼图"""
        labels = data.get('labels', [])
        datasets = data.get('datasets', [])
        
        if datasets:
            values = datasets[0].get('data', [])
            # 创建字体属性对象
            from matplotlib.font_manager import FontProperties
            font_prop = FontProperties(family='Microsoft YaHei')
            
            ax.pie(values, labels=labels, colors=colors[:len(values)], 
                  autopct='%1.1f%%', startangle=90,
                  textprops={'fontproperties': font_prop})
    
    async def _create_scatter_chart(self, ax, data, colors):
        """创建散点图"""
        datasets = data.get('datasets', [])
        
        for i, dataset in enumerate(datasets):
            points = dataset.get('data', [])
            label = dataset.get('label', f'数据集{i+1}')
            color = colors[i % len(colors)]
            
            x_values = [point['x'] for point in points]
            y_values = [point['y'] for point in points]
            
            ax.scatter(x_values, y_values, label=label, color=color, 
                      s=60, alpha=0.7)
        
        ax.legend(prop={'family': 'Microsoft YaHei'})
    
    def _apply_theme(self, fig, ax, theme: str):
        """应用主题"""
        # 确保字体设置在主题应用时也生效
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        if theme == 'dark':
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        elif theme == 'minimal':
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.3)
    
    async def _generate_chart_code_with_ai(self, description: str, chart_type: str) -> str:
        """
        使用AI生成图表代码（这里是示例，实际需要调用LLM）
        """
        # 这里应该调用LLM生成代码，现在提供示例
        if chart_type == 'mermaid':
            # 简单的示例生成
            if 'flow' in description.lower() or '流程' in description:
                return f"""graph TD
    A[开始] --> B[{description}]
    B --> C[处理]
    C --> D[结束]"""
            elif 'sequence' in description.lower() or '时序' in description:
                return f"""sequenceDiagram
    participant A as 用户
    participant B as 系统
    A->>B: {description}
    B-->>A: 响应"""
            else:
                return f"""graph LR
    A[{description}] --> B[处理]
    B --> C[结果]"""
        
        return ""
    
    async def _generate_chart_data_with_ai(
        self, 
        description: str, 
        chart_type: str, 
        data_source: Optional[str] = None
    ) -> str:
        """
        根据图表类型生成示例数据（简化版本）
        """
        logger.info(f"AI生成示例数据: 图表类型={chart_type}, 描述={description}")
        
        # 根据图表类型生成对应的示例数据
        if chart_type == 'bar':
            return json.dumps({
                "labels": ["类别A", "类别B", "类别C", "类别D", "类别E"],
                "datasets": [{
                    "label": description or "数据系列",
                    "data": [65, 59, 80, 81, 56]
                }]
            })
        elif chart_type == 'pie':
            return json.dumps({
                "labels": ["部分A", "部分B", "部分C", "部分D"],
                "datasets": [{
                    "data": [30, 25, 25, 20]
                }]
            })
        elif chart_type == 'line':
            return json.dumps({
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
                "datasets": [{
                    "label": description or "趋势数据",
                    "data": [65, 59, 80, 81, 56, 78]
                }]
            })
        elif chart_type == 'scatter':
            return json.dumps({
                "datasets": [{
                    "label": description or "散点数据",
                    "data": [
                        {"x": 10, "y": 20},
                        {"x": 15, "y": 25},
                        {"x": 20, "y": 30},
                        {"x": 25, "y": 35},
                        {"x": 30, "y": 40}
                    ]
                }]
            })
        else:
            # 默认返回柱状图数据
            return json.dumps({
                "labels": ["项目1", "项目2", "项目3"],
                "datasets": [{
                    "label": description or "默认数据",
                    "data": [10, 20, 30]
                }]
            })
    
    async def _generate_sample_data_from_description(self, description: str, chart_type: str) -> Dict[str, Any]:
        """
        根据描述和图表类型生成示例数据
        """
        logger.info(f"根据描述生成示例数据: {description} -> {chart_type}")
        
        # 根据图表类型生成对应的示例数据
        if chart_type == 'bar':
            return {
                "labels": ["类别A", "类别B", "类别C", "类别D", "类别E"],
                "datasets": [{
                    "label": description or "数据系列",
                    "data": [65, 59, 80, 81, 56]
                }]
            }
        elif chart_type == 'pie':
            return {
                "labels": ["部分A", "部分B", "部分C", "部分D"],
                "datasets": [{
                    "data": [30, 25, 25, 20]
                }]
            }
        elif chart_type == 'line':
            return {
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
                "datasets": [{
                    "label": description or "趋势数据",
                    "data": [65, 59, 80, 81, 56, 78]
                }]
            }
        elif chart_type == 'scatter':
            return {
                "datasets": [{
                    "label": description or "散点数据",
                    "data": [
                        {"x": 10, "y": 20},
                        {"x": 15, "y": 25},
                        {"x": 20, "y": 30},
                        {"x": 25, "y": 35},
                        {"x": 30, "y": 40}
                    ]
                }]
            }
        else:
            # 默认返回柱状图数据
            return {
                "labels": ["项目1", "项目2", "项目3"],
                "datasets": [{
                    "label": description or "默认数据",
                    "data": [10, 20, 30]
                }]
            }


# 创建 FastAPI 应用
app = FastAPI(
    title="Chart Generator Service", 
    description="图表生成器服务",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4396", "http://127.0.0.1:4396"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建图表生成器实例
chart_generator = ChartGenerator()


@app.get("/")
async def root():
    """服务健康检查"""
    return {
        "service": "Chart Generator",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    return {
        "service": "Chart Generator",
        "status": "running",
        "output_dir": str(chart_generator.output_dir),
        "output_dir_exists": chart_generator.output_dir.exists()
    }


@app.post("/generate_chart")
async def generate_chart(request: ChartRequest) -> Dict[str, Any]:
    """
    生成图表
    
    Args:
        request: 图表生成请求
        
    Returns:
        Dict[str, Any]: 生成结果
    """
    result = await chart_generator.generate_chart(
        chart_type=request.chart_type,
        data=request.data,
        title=request.title,
        width=request.width or 800,
        height=request.height or 600,
        theme=request.theme or "default",
        color_scheme=request.color_scheme or "blue",
        style_options=request.style_options
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result)
    
    return result


@app.post("/generate_chart_with_ai")
async def generate_chart_with_ai(request: ChartAIRequest) -> Dict[str, Any]:
    """
    使用AI生成图表
    
    Args:
        request: AI图表生成请求
        
    Returns:
        Dict[str, Any]: 生成结果
    """
    result = await chart_generator.generate_chart_with_ai(
        description=request.description,
        chart_type=request.chart_type,
        data_source=request.data_source,
        style_preferences=request.style_preferences
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result)
    
    return result


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载生成的图表文件
    
    Args:
        filename: 文件名
        
    Returns:
        FileResponse: 图表文件
    """
    file_path = chart_generator.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='image/png'
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动图表生成器服务...")
    uvicorn.run(app, host="0.0.0.0", port=8003) 