"""
LaTeX Beamer PPT 生成器 MCP 服务
使用 FastMCP 框架提供 PPT 生成功能
"""

import os
import subprocess
import tempfile
import shutil
import zipfile
import tarfile
import gzip
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger
import requests
import json
import openai


class PPTRequest(BaseModel):
    """PPT 生成请求模型"""
    latex_content: str  # 直接接收生成好的LaTeX内容
    title: Optional[str] = None


class PPTContentRequest(BaseModel):
    """基于内容生成PPT的请求模型"""
    content: str  # 文本内容
    title: Optional[str] = None
    theme: Optional[str] = "academic"
    language: Optional[str] = "zh-CN"
    slides_count: Optional[int] = 10


class PPTProjectRequest(BaseModel):
    """PPT 项目生成请求模型（包含资源文件）"""
    main_tex_filename: str  # 主LaTeX文件名
    title: Optional[str] = None


class PPTGenerator:
    """
    PPT 生成器类
    负责将文本内容转换为 LaTeX Beamer 演示文稿
    """
    
    def __init__(self):
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        self.agent_api_url = "http://localhost:8001"  # Agent核心服务地址
        self.backend_api_url = "http://localhost:8000"  # 后端服务地址
    
    def _is_supported_archive(self, filename: str) -> bool:
        """检查文件是否为支持的压缩格式"""
        filename = filename.lower()
        return (filename.endswith('.zip') or 
                filename.endswith('.tar.gz') or 
                filename.endswith('.tgz') or 
                filename.endswith('.gz'))
    
    async def _extract_archive(self, archive_file: UploadFile, extract_path: Path) -> List[str]:
        """
        通用的压缩文件解压函数
        
        Args:
            archive_file: 压缩文件
            extract_path: 解压目标路径
            
        Returns:
            List[str]: 解压后的文件列表
        """
        filename = archive_file.filename.lower()
        
        # 创建临时文件保存压缩包
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await archive_file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        try:
            extracted_files = []
            
            if filename.endswith('.zip'):
                logger.info("解压ZIP文件...")
                with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    extracted_files = zip_ref.namelist()
                    
            elif filename.endswith('.tar.gz') or filename.endswith('.tgz'):
                logger.info("解压TAR.GZ文件...")
                with tarfile.open(temp_file_path, 'r:gz') as tar_ref:
                    # 安全解压（防止路径遍历攻击）
                    members = tar_ref.getmembers()
                    safe_members = []
                    for member in members:
                        if member.isfile() or member.isdir():
                            # 规范化路径
                            safe_path = Path(extract_path) / member.name
                            if str(safe_path).startswith(str(extract_path)):
                                safe_members.append(member)
                                extracted_files.append(member.name)
                            else:
                                logger.warning(f"跳过不安全路径: {member.name}")
                    tar_ref.extractall(extract_path, members=safe_members)
                    
            elif filename.endswith('.gz'):
                logger.info("解压GZ文件...")
                # 对于.gz文件，通常是单个文件的压缩
                # 需要确定原始文件名，只取文件名部分，不包含路径
                original_name = Path(filename).name[:-3]  # 移除.gz后缀，只保留文件名
                if not original_name:
                    original_name = "extracted_file"
                
                output_file = extract_path / original_name
                
                with gzip.open(temp_file_path, 'rb') as gz_file:
                    with open(output_file, 'wb') as out_file:
                        shutil.copyfileobj(gz_file, out_file)
                
                extracted_files = [original_name]
                
            else:
                raise ValueError(f"不支持的文件格式: {filename}")
                
            logger.info(f"解压完成，共 {len(extracted_files)} 个文件")
            return extracted_files
            
        except zipfile.BadZipFile as e:
            logger.error(f"无效的ZIP文件: {e}")
            raise HTTPException(status_code=400, detail=f"无效的ZIP文件: {str(e)}")
        except tarfile.TarError as e:
            logger.error(f"无效的TAR.GZ文件: {e}")
            raise HTTPException(status_code=400, detail=f"无效的TAR.GZ文件: {str(e)}")
        except gzip.BadGzipFile as e:
            logger.error(f"无效的GZ文件: {e}")
            raise HTTPException(status_code=400, detail=f"无效的GZ文件: {str(e)}")
        except Exception as e:
            logger.error(f"解压文件时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"解压文件失败: {str(e)}")
        finally:
            # 清理临时文件
            if temp_file_path.exists():
                temp_file_path.unlink()
        
    async def generate_ppt(
        self,
        latex_content: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成 PPT 演示文稿（单文件模式）
        
        Args:
            latex_content: 完整的LaTeX Beamer内容
            title: 演示文稿标题
            
        Returns:
            Dict[str, Any]: 生成结果，包含文件路径或错误信息
        """
        try:
            logger.info(f"开始编译 LaTeX PPT: title={title}")
            
            # 直接编译LaTeX内容
            pdf_path = await self._compile_latex_to_pdf(latex_content, title or "presentation")
            
            result = {
                "success": True,
                "pdf_path": str(pdf_path),
                "title": title,
            }
            
            logger.info(f"PPT 生成成功: {pdf_path}")
            return result
            
        except Exception as e:
            logger.error(f"PPT 生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def generate_ppt_from_project(
        self,
        project_files: List[UploadFile],
        main_tex_filename: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从项目文件夹生成 PPT 演示文稿（支持资源文件）
        
        Args:
            project_files: 项目文件列表
            main_tex_filename: 主LaTeX文件名
            title: 演示文稿标题
            
        Returns:
            Dict[str, Any]: 生成结果，包含文件路径或错误信息
        """
        try:
            logger.info(f"开始编译 LaTeX 项目 PPT: title={title}, main_file={main_tex_filename}")
            
            # 编译LaTeX项目
            pdf_path = await self._compile_latex_project_to_pdf(
                project_files, main_tex_filename, title or "presentation"
            )
            
            result = {
                "success": True,
                "pdf_path": str(pdf_path),
                "title": title,
                "main_file": main_tex_filename,
                "files_count": len(project_files)
            }
            
            logger.info(f"PPT 项目生成成功: {pdf_path}")
            return result
            
        except Exception as e:
            logger.error(f"PPT 项目生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def generate_ppt_from_content(
        self,
        content: str,
        title: Optional[str] = None,
        theme: str = "academic",
        language: str = "zh-CN",
        slides_count: int = 10
    ) -> Dict[str, Any]:
        """
        基于文本内容生成PPT（AI生成LaTeX）
        
        Args:
            content: 文本内容
            title: 演示文稿标题
            theme: 主题风格
            language: 语言
            slides_count: 幻灯片数量
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            logger.info(f"开始基于内容生成PPT: title={title}, theme={theme}")
            
            # 调用Agent API生成LaTeX内容
            latex_content = await self._generate_latex_with_ai(
                content, title, theme, language, slides_count
            )
            
            # 编译LaTeX为PDF
            pdf_path = await self._compile_latex_to_pdf(latex_content, title or "presentation")
            
            result = {
                "success": True,
                "pdf_path": str(pdf_path),
                "title": title,
                "theme": theme,
                "slides_count": slides_count,
                "latex_content": latex_content[:500] + "..." if len(latex_content) > 500 else latex_content
            }
            
            logger.info(f"基于内容的PPT生成成功: {pdf_path}")
            return result
            
        except Exception as e:
            logger.error(f"基于内容的PPT生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def _generate_latex_with_ai(
        self,
        content: str,
        title: Optional[str] = None,
        theme: str = "academic",
        language: str = "zh-CN",
        slides_count: int = 10
    ) -> str:
        """
        使用AI生成LaTeX Beamer内容（已废弃，现在由Agent管理器处理）
        """
        raise Exception("此方法已废弃，请通过后端API创建任务，由Agent管理器处理AI生成")
    
    def _build_latex_prompt(
        self,
        content: str,
        title: Optional[str] = None,
        theme: str = "academic",
        language: str = "zh-CN",
        slides_count: int = 10
    ) -> str:
        """构建LaTeX生成提示词"""
        
        theme_settings = {
            "academic": "\\usetheme{Madrid}\\usecolortheme{default}",
            "business": "\\usetheme{CambridgeUS}\\usecolortheme{beaver}",
            "modern": "\\usetheme{metropolis}",
            "creative": "\\usetheme{Berlin}\\usecolortheme{seahorse}",
            "minimal": "\\usetheme{default}"
        }
        
        theme_code = theme_settings.get(theme, theme_settings["academic"])
        
        prompt = f"""请基于以下内容生成一个完整的LaTeX Beamer演示文稿代码。

要求：
1. 使用中文字体支持（xeCJK包）
2. 主题：{theme} ({theme_code})
3. 语言：{language}
4. 目标幻灯片数量：约{slides_count}张
5. 标题：{title or "演示文稿"}

内容：
{content}

请生成完整的LaTeX代码，包括：
- 文档类声明和包导入
- 中文字体设置
- 主题设置
- 标题页
- 目录页（如果需要）
- 内容页面（根据内容自动分段）
- 结束页

确保代码可以直接编译，使用xelatex编译器。请只返回LaTeX代码，不要包含其他解释文字。

```latex
\\documentclass[aspectratio=169]{{beamer}}
\\usepackage{{xeCJK}}
\\setCJKmainfont{{SimSun}}
{theme_code}

\\title{{{title or "演示文稿"}}}
\\author{{AI生成}}
\\date{{\\today}}

\\begin{{document}}

\\frame{{\\titlepage}}

% 在这里继续生成内容...
```"""
        
        return prompt
    
    def _extract_latex_code(self, response: str) -> str:
        """从AI响应中提取LaTeX代码"""
        # 查找代码块
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
    

    
    async def generate_ppt_from_latex_project(
        self,
        original_latex_content: str,
        project_files: List[UploadFile],
        main_tex_filename: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于LaTeX项目生成PPT（AI转换为Beamer格式）
        
        Args:
            original_latex_content: 原始LaTeX文件内容
            project_files: 项目文件列表（包含图片等资源）
            main_tex_filename: 主LaTeX文件名
            title: 演示文稿标题
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            logger.info(f"开始基于LaTeX项目生成PPT: title={title}, main_file={main_tex_filename}")
            
            # 使用AI将原始LaTeX转换为Beamer格式
            beamer_content = await self._convert_latex_to_beamer(
                original_latex_content, title
            )
            
            # 编译Beamer代码与项目资源文件
            pdf_path = await self._compile_beamer_with_resources(
                beamer_content, project_files, main_tex_filename, title or "presentation"
            )
            
            result = {
                "success": True,
                "pdf_path": str(pdf_path),
                "title": title,
                "main_file": main_tex_filename,
                "files_count": len(project_files),
                "conversion_type": "latex_to_beamer"
            }
            
            logger.info(f"LaTeX项目PPT生成成功: {pdf_path}")
            return result
            
        except Exception as e:
            logger.error(f"LaTeX项目PPT生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def _convert_latex_to_beamer(
        self,
        original_latex_content: str,
        title: Optional[str] = None
    ) -> str:
        """
        使用AI将原始LaTeX内容转换为Beamer演示文稿格式
        """
        try:
            # 直接创建一个文档内容转换任务，而不是LaTeX项目任务
            task_data = {
                "title": title or "LaTeX转Beamer任务",
                "description": f"将LaTeX文档转换为Beamer演示文稿",
                "tool_type": "ppt_generator",
                "parameters": {
                    "content": original_latex_content,
                    "title": title,
                    "input_type": "document_content",  # 改为文档内容类型
                    "theme": "academic",
                    "language": "zh-CN"
                }
            }
            
            # 调用后端创建任务API
            response = requests.post(
                f"{self.backend_api_url}/api/tasks/",
                json=task_data,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"后端任务创建失败: HTTP {response.status_code}")
            
            task_result = response.json()
            task_id = task_result.get("id")
            
            if not task_id:
                raise Exception("任务创建失败，未获取到任务ID")
            
            logger.info(f"LaTeX转换任务已创建: {task_id}")
            
            # 等待任务完成（轮询检查）
            import time
            max_wait_time = 300  # 最大等待5分钟，因为转换可能需要更长时间
            check_interval = 3   # 每3秒检查一次
            waited_time = 0
            
            while waited_time < max_wait_time:
                # 检查任务状态
                status_response = requests.get(
                    f"{self.backend_api_url}/api/tasks/{task_id}",
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    task_info = status_response.json()
                    status = task_info.get("status")
                    
                    if status == "completed":
                        # 任务完成，提取LaTeX内容
                        result = task_info.get("result", {})
                        beamer_content = result.get("latex_content", "")
                        if not beamer_content:
                            raise Exception("AI生成的Beamer内容为空")
                        return beamer_content
                    elif status == "failed":
                        error_msg = task_info.get("error_message", "未知错误")
                        raise Exception(f"AI转换失败: {error_msg}")
                    
                    # 任务还在进行中，继续等待
                    time.sleep(check_interval)
                    waited_time += check_interval
                else:
                    raise Exception(f"获取任务状态失败: HTTP {status_response.status_code}")
            
            # 超时
            raise Exception("AI转换超时，请稍后重试")
            
        except Exception as e:
            logger.error(f"AI转换LaTeX到Beamer失败: {e}")
            raise Exception(f"AI转换LaTeX到Beamer失败: {e}")
    
    def _build_latex_to_beamer_prompt(
        self,
        original_latex_content: str,
        title: Optional[str] = None
    ) -> str:
        """构建LaTeX到Beamer转换的提示词"""
        
        prompt = f"""请将以下LaTeX学术论文内容转换为LaTeX Beamer演示文稿格式。

要求：
1. 保持原有的图片引用路径不变（如 \\includegraphics{{Example.png}}）
2. 保持原有的引用格式（如 \\cite{{}}、\\ref{{}}等）
3. 使用中文字体支持（xeCJK包）
4. 使用学术风格主题
5. 标题：{title or "学术演示"}
6. 将内容合理分割为多个幻灯片
7. 保留重要的数学公式和表格
8. 为每个主要章节创建单独的幻灯片

原始LaTeX内容：
```latex
{original_latex_content}
```

请生成完整的LaTeX Beamer代码，确保：
- 文档类为 \\documentclass[aspectratio=169]{{beamer}}
- 包含必要的包导入
- 设置中文字体
- 包含标题页
- 将内容分割为合适的幻灯片
- 保持所有图片和引用的原始路径

请只返回LaTeX代码，不要包含其他解释文字。

```latex
\\documentclass[aspectratio=169]{{beamer}}
\\usepackage{{xeCJK}}
\\setCJKmainfont{{SimSun}}
\\usetheme{{Madrid}}
\\usecolortheme{{default}}

\\title{{{title or "学术演示"}}}
\\author{{研究团队}}
\\date{{\\today}}

\\begin{{document}}

\\frame{{\\titlepage}}

% 在这里继续生成内容...
```"""
        
        return prompt
    
    async def _generate_beamer_from_project_direct(
        self,
        original_latex_content: str,
        project_files: List[UploadFile],
        main_tex_filename: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        直接在本地使用AI转换LaTeX为Beamer并编译（包含资源文件）
        这个方法不通过后端API，直接在PPT服务内完成所有操作
        """
        try:
            logger.info(f"开始本地LaTeX项目转Beamer: title={title}, main_file={main_tex_filename}")
            
            # 使用简化的转换逻辑，直接编译原始LaTeX项目
            # 对于LaTeX项目，我们直接编译，不进行AI转换
            # 因为AI转换需要调用后端API，会导致循环依赖
            
            # 直接编译LaTeX项目
            pdf_path = await self._compile_latex_project_to_pdf(
                project_files, main_tex_filename, title or "presentation"
            )
            
            result = {
                "success": True,
                "pdf_path": str(pdf_path),
                "title": title,
                "main_file": main_tex_filename,
                "files_count": len(project_files),
                "conversion_type": "direct_latex_compilation"
            }
            
            logger.info(f"LaTeX项目直接编译成功: {pdf_path}")
            return result
            
        except Exception as e:
            logger.error(f"LaTeX项目直接编译失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def _compile_beamer_with_resources(
        self,
        beamer_content: str,
        project_files: List[UploadFile],
        main_tex_filename: str,
        filename: str
    ) -> Path:
        """
        编译Beamer代码与项目资源文件
        """
        # 检查 xelatex 是否安装
        try:
            subprocess.run(["xelatex", "-v"], check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("未安装 xelatex 编译器。请安装 TeX Live 或 MiKTeX。")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 先保存所有项目文件到临时目录（除了主tex文件）
            for file in project_files:
                if file.filename != main_tex_filename:  # 跳过主tex文件，我们会用AI生成的版本
                    file_path = temp_path / file.filename
                    
                    # 创建必要的子目录
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 重置文件指针并保存文件
                    await file.seek(0)  # 使用await确保异步操作完成
                    content = await file.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    logger.debug(f"保存资源文件: {file.filename}")
            
            # 使用安全的文件名
            import hashlib
            safe_filename = hashlib.md5(filename.encode('utf-8')).hexdigest()
            
            # 写入AI生成的Beamer文件
            beamer_file = temp_path / f"{safe_filename}.tex"
            try:
                with open(beamer_file, 'w', encoding='utf-8') as f:
                    f.write(beamer_content)
                logger.info(f"AI生成的Beamer文件已保存: {beamer_file}")
            except Exception as e:
                logger.error(f"写入 Beamer 文件失败: {e}")
                raise Exception(f"写入 Beamer 文件失败: {e}")
            
            # 编译为 PDF
            pdf_path = await self._run_latex_compilation(temp_path, beamer_file, safe_filename)
            
            # 移动 PDF 到输出目录
            pdf_target = self.output_dir / f"{filename}.pdf"
            try:
                # 使用 shutil.copy2 代替 rename 以支持跨磁盘移动
                shutil.copy2(pdf_path, pdf_target)
                logger.info(f"PDF 文件已复制到: {pdf_target}")
                return pdf_target
            except Exception as e:
                logger.error(f"移动PDF文件失败: {e}")
                raise Exception(f"移动PDF文件失败: {e}")

    async def _compile_latex_to_pdf(self, latex_content: str, filename: str) -> Path:
        """
        直接编译LaTeX内容为PDF（单文件模式）
        
        Args:
            latex_content: 完整的LaTeX内容
            filename: 文件名
            
        Returns:
            Path: PDF 文件路径
        """
        # 检查 xelatex 是否安装
        try:
            subprocess.run(["xelatex", "-v"], check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("未安装 xelatex 编译器。请安装 TeX Live 或 MiKTeX。")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 使用安全的文件名（避免中文字符）
            import hashlib
            safe_filename = hashlib.md5(filename.encode('utf-8')).hexdigest()
            
            # 写入LaTeX文件
            tex_file = temp_path / f"{safe_filename}.tex"
            try:
                with open(tex_file, 'w', encoding='utf-8') as f:
                    f.write(latex_content)
            except Exception as e:
                logger.error(f"写入 LaTeX 文件失败: {e}")
                raise Exception(f"写入 LaTeX 文件失败: {e}")
            
            # 编译为 PDF
            pdf_path = await self._run_latex_compilation(temp_path, tex_file, safe_filename)
            
            # 移动 PDF 到输出目录
            pdf_target = self.output_dir / f"{filename}.pdf"
            try:
                # 使用 shutil.copy2 代替 rename 以支持跨磁盘移动
                shutil.copy2(pdf_path, pdf_target)
                logger.info(f"PDF 文件已复制到: {pdf_target}")
                return pdf_target
            except Exception as e:
                logger.error(f"移动PDF文件失败: {e}")
                raise Exception(f"移动PDF文件失败: {e}")

    async def _compile_latex_project_to_pdf(
        self, 
        project_files: List[UploadFile], 
        main_tex_filename: str, 
        filename: str
    ) -> Path:
        """
        编译LaTeX项目为PDF（支持资源文件）
        
        Args:
            project_files: 项目文件列表
            main_tex_filename: 主LaTeX文件名
            filename: 输出文件名
            
        Returns:
            Path: PDF 文件路径
        """
        # 检查 xelatex 是否安装
        try:
            subprocess.run(["xelatex", "-v"], check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("未安装 xelatex 编译器。请安装 TeX Live 或 MiKTeX。")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 保存所有项目文件到临时目录
            main_tex_file = None
            for file in project_files:
                file_path = temp_path / file.filename
                
                # 创建必要的子目录
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 重置文件指针并保存文件
                await file.seek(0)  # 使用await确保异步操作完成
                content = await file.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # 记录主LaTeX文件
                if file.filename == main_tex_filename:
                    main_tex_file = file_path
                
                logger.debug(f"保存项目文件: {file.filename}")
            
            # 检查主LaTeX文件是否存在
            if main_tex_file is None:
                raise Exception(f"未找到主LaTeX文件: {main_tex_filename}")
            
            # 使用安全的文件名
            import hashlib
            safe_filename = hashlib.md5(filename.encode('utf-8')).hexdigest()
            
            # 编译为 PDF
            pdf_path = await self._run_latex_compilation(temp_path, main_tex_file, safe_filename)
            
            # 移动 PDF 到输出目录
            pdf_target = self.output_dir / f"{filename}.pdf"
            try:
                # 使用 shutil.copy2 代替 rename 以支持跨磁盘移动
                shutil.copy2(pdf_path, pdf_target)
                logger.info(f"PDF 文件已复制到: {pdf_target}")
                return pdf_target
            except Exception as e:
                logger.error(f"移动PDF文件失败: {e}")
                raise Exception(f"移动PDF文件失败: {e}")

    async def _run_latex_compilation(self, work_dir: Path, tex_file: Path, output_name: str) -> Path:
        """
        运行LaTeX编译
        
        Args:
            work_dir: 工作目录
            tex_file: LaTeX文件路径
            output_name: 输出文件名
            
        Returns:
            Path: 生成的PDF文件路径
        """
        try:
            # 第一次编译
            result = subprocess.run([
                "xelatex",
                "-interaction=nonstopmode",
                "-output-directory", str(work_dir),
                "-jobname", output_name,  # 指定输出文件名
                str(tex_file)
            ], check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', cwd=work_dir)
            
            # 再次编译以确保引用正确
            subprocess.run([
                "xelatex",
                "-interaction=nonstopmode", 
                "-output-directory", str(work_dir),
                "-jobname", output_name,
                str(tex_file)
            ], check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', cwd=work_dir)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"xelatex 编译失败: {e}")
            logger.error(f"编译输出: {e.stdout}")
            logger.error(f"编译错误: {e.stderr}")
            
            # 提供更详细的错误信息
            if "Image inclusion failed" in e.stderr:
                raise Exception("LaTeX 编译失败：找不到引用的图片文件。请确保所有图片文件都已上传。")
            elif "font" in e.stderr.lower() or "cjk" in e.stderr.lower():
                raise Exception("LaTeX 编译失败：可能是中文字体问题。请确保系统已安装中文字体包。")
            elif "Missing \\begin{document}" in e.stderr:
                raise Exception("LaTeX 编译失败：LaTeX文件格式错误，可能包含非LaTeX内容。")
            else:
                raise Exception(f"LaTeX 编译失败: {e.stderr}")
        
        # 检查PDF文件是否生成
        pdf_file = work_dir / f"{output_name}.pdf"
        if pdf_file.exists():
            return pdf_file
        else:
            raise Exception("PDF 文件生成失败：编译完成但未找到输出文件")


# 创建 FastAPI 应用
app = FastAPI(
    title="PPT Generator Service", 
    description="LaTeX Beamer PPT 生成器服务",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4396", "http://127.0.0.1:4396"],  # 允许前端访问
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 创建 PPT 生成器实例
ppt_generator = PPTGenerator()


@app.get("/")
async def root():
    """服务健康检查"""
    return {
        "service": "PPT Generator",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    # 检查 xelatex 是否可用
    latex_available = False
    latex_version = "未安装"
    
    try:
        result = subprocess.run(["xelatex", "-v"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            latex_available = True
            latex_version = "xelatex 可用"
    except FileNotFoundError:
        pass
    
    return {
        "service": "PPT Generator",
        "status": "running",
        "xelatex_available": latex_available,
        "latex_version": latex_version,
        "output_dir": str(ppt_generator.output_dir),
        "output_dir_exists": ppt_generator.output_dir.exists()
    }


@app.post("/generate_ppt")
async def generate_ppt(request: PPTRequest) -> Dict[str, Any]:
    """
    编译 LaTeX Beamer PPT 演示文稿
    
    Args:
        request: PPT 生成请求，包含LaTeX内容和标题
        
    Returns:
        Dict[str, Any]: 生成结果，包含 PDF 文件路径或错误信息
    """
    result = await ppt_generator.generate_ppt(
        request.latex_content, 
        request.title
    )
    
    # 如果生成失败，返回 500 错误
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result)
    
    return result


@app.post("/generate_ppt_from_content")
async def generate_ppt_from_content(request: PPTContentRequest) -> Dict[str, Any]:
    """
    基于文本内容生成PPT（已废弃，请使用后端API创建任务）
    
    Args:
        request: PPT内容生成请求
        
    Returns:
        Dict[str, Any]: 错误信息
    """
    raise HTTPException(
        status_code=400, 
        detail="此接口已废弃，请通过后端API创建任务：POST /api/tasks/ 使用 tool_type='ppt_generator'"
    )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载生成的PDF文件
    
    Args:
        filename: 文件名
        
    Returns:
        FileResponse: PDF文件
    """
    file_path = ppt_generator.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/pdf'
    )


@app.post("/generate_ppt_from_project")
async def generate_ppt_from_project(
    files: List[UploadFile] = File(...),
    main_tex_filename: str = Form(...),
    title: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    从项目文件夹生成 PPT 演示文稿（支持资源文件）
    
    Args:
        files: 项目文件列表
        main_tex_filename: 主LaTeX文件名
        title: 演示文稿标题
        
    Returns:
        Dict[str, Any]: 生成结果，包含 PDF 文件路径或错误信息
    """
    result = await ppt_generator.generate_ppt_from_project(
        files, main_tex_filename, title
    )
    
    # 如果生成失败，返回 500 错误
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result)
    
    return result


@app.post("/upload_and_generate")
async def upload_and_generate(
    archive_file: UploadFile = File(...),
    main_tex_filename: str = Form(default=""),
    title: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    上传压缩文件并生成PPT（推荐方式）
    
    Args:
        archive_file: 包含LaTeX项目的压缩文件（支持.zip, .tar.gz, .tgz）
        main_tex_filename: 主LaTeX文件名（可选，会自动检测）
        title: 演示文稿标题
        
    Returns:
        Dict[str, Any]: 生成结果
    """
    filename = archive_file.filename.lower()
    if not ppt_generator._is_supported_archive(filename):
        raise HTTPException(status_code=400, detail="请上传ZIP、TAR.GZ、TGZ或GZ格式的文件")
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 解压文件
            extract_path = temp_path / "extracted"
            extract_path.mkdir()
            
            # 重置文件指针
            await archive_file.seek(0)
            
            # 使用通用解压函数
            extracted_file_names = await ppt_generator._extract_archive(archive_file, extract_path)
            
            # 自动检测LaTeX文件
            tex_files = []
            project_files = []
            
            for file_path in extract_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(extract_path)
                    
                    # 收集所有tex文件
                    if str(relative_path).endswith('.tex'):
                        tex_files.append(str(relative_path))
                    
                    # 创建模拟的UploadFile对象
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # 创建临时UploadFile
                    mock_file = UploadFile(
                        filename=str(relative_path),
                        file=BytesIO(file_content)
                    )
                    project_files.append(mock_file)
            
            # 自动检测主LaTeX文件
            detected_main_tex = None
            if not main_tex_filename:
                # 按优先级查找主文件
                priority_names = ['main.tex', 'paper.tex', 'document.tex', 'presentation.tex', 'slides.tex']
                for priority_name in priority_names:
                    if priority_name in tex_files:
                        detected_main_tex = priority_name
                        break
                
                # 如果没找到优先级文件，使用第一个tex文件
                if not detected_main_tex and tex_files:
                    detected_main_tex = tex_files[0]
                
                if detected_main_tex:
                    main_tex_filename = detected_main_tex
                    logger.info(f"自动检测到主LaTeX文件: {main_tex_filename}")
            
            # 验证主LaTeX文件是否存在
            if not main_tex_filename:
                if not tex_files:
                    raise HTTPException(
                        status_code=400, 
                        detail="压缩文件中未找到任何.tex文件"
                    )
                else:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"无法确定主LaTeX文件，请指定。找到的tex文件: {', '.join(tex_files)}"
                    )
            
            if main_tex_filename not in tex_files:
                raise HTTPException(
                    status_code=400, 
                    detail=f"指定的主LaTeX文件 '{main_tex_filename}' 不存在。找到的tex文件: {', '.join(tex_files)}"
                )
            
            # 读取主LaTeX文件内容
            main_tex_content = None
            for file in project_files:
                if file.filename == main_tex_filename:
                    # 重置文件指针
                    await file.seek(0)
                    content = await file.read()
                    main_tex_content = content.decode('utf-8', errors='ignore')
                    break
            
            if not main_tex_content:
                raise HTTPException(
                    status_code=400, 
                    detail=f"无法读取主LaTeX文件内容: {main_tex_filename}"
                )
            
            # 使用AI转换LaTeX为Beamer并编译（包含资源文件）
            result = await ppt_generator._generate_beamer_from_project_direct(
                main_tex_content, project_files, main_tex_filename, title
            )
            
            # 检查生成是否成功
            if not result.get("success", False):
                logger.error(f"PPT生成失败: {result}")
                raise HTTPException(status_code=500, detail=result.get("error", "PPT生成失败"))
            
            # 添加检测信息到结果中
            result["detected_tex_files"] = tex_files
            result["used_main_tex"] = main_tex_filename
            result["auto_detected"] = detected_main_tex is not None
            
            return result
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的ZIP文件")
    except tarfile.TarError:
        raise HTTPException(status_code=400, detail="无效的TAR.GZ文件")
    except Exception as e:
        logger.error(f"处理压缩文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/detect_tex_files")
async def detect_tex_files(
    archive_file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    检测压缩文件中的LaTeX文件
    
    Args:
        archive_file: 包含LaTeX项目的压缩文件（支持.zip, .tar.gz, .tgz, .gz）
        
    Returns:
        Dict[str, Any]: 检测结果
    """
    filename = archive_file.filename.lower()
    if not ppt_generator._is_supported_archive(filename):
        raise HTTPException(status_code=400, detail="请上传ZIP、TAR.GZ、TGZ或GZ格式的文件")
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 解压文件
            extract_path = temp_path / "extracted"
            extract_path.mkdir()
            
            # 使用通用解压函数
            extracted_file_names = await ppt_generator._extract_archive(archive_file, extract_path)
            
            # 检测LaTeX文件
            tex_files = []
            all_files = []
            
            for file_path in extract_path.rglob('*'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(extract_path))
                    all_files.append(relative_path)
                    
                    if relative_path.endswith('.tex'):
                        tex_files.append(relative_path)
            
            # 自动检测主LaTeX文件
            suggested_main_tex = None
            priority_names = ['main.tex', 'paper.tex', 'document.tex', 'presentation.tex', 'slides.tex']
            for priority_name in priority_names:
                if priority_name in tex_files:
                    suggested_main_tex = priority_name
                    break
            
            # 如果没找到优先级文件，使用第一个tex文件
            if not suggested_main_tex and tex_files:
                suggested_main_tex = tex_files[0]
            
            return {
                "success": True,
                "tex_files": tex_files,
                "suggested_main_tex": suggested_main_tex,
                "total_files": len(all_files),
                "archive_type": "zip" if filename.endswith('.zip') else "tar.gz"
            }
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的ZIP文件")
    except tarfile.TarError:
        raise HTTPException(status_code=400, detail="无效的TAR.GZ文件")
    except Exception as e:
        logger.error(f"检测压缩文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@app.get("/themes")
async def list_themes() -> Dict[str, Any]:
    """
    获取可用的 PPT 主题列表
    
    Returns:
        Dict[str, Any]: 主题列表
    """
    return {
        "message": "PPT主题现在由AI Agent根据用户需求智能选择",
        "themes": [
            {"name": "default", "description": "默认主题"},
            {"name": "modern", "description": "现代主题"},
            {"name": "academic", "description": "学术主题"},
        ]
    }


@app.post("/extract_tex_content")
async def extract_tex_content(
    archive_file: UploadFile = File(...),
    main_tex_filename: str = Form(...)
) -> Dict[str, Any]:
    """
    从压缩文件中提取指定LaTeX文件的内容
    
    Args:
        archive_file: 包含LaTeX项目的压缩文件
        main_tex_filename: 主LaTeX文件名
        
    Returns:
        Dict[str, Any]: 提取结果，包含LaTeX内容
    """
    logger.info(f"开始提取LaTeX内容: 文件={archive_file.filename}, 主文件={main_tex_filename}")
    
    if not archive_file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
        
    filename = archive_file.filename.lower()
    logger.info(f"处理文件类型: {filename}")
    
    if not ppt_generator._is_supported_archive(filename):
        raise HTTPException(status_code=400, detail="请上传ZIP、TAR.GZ、TGZ或GZ格式的文件")
    
    if not main_tex_filename or main_tex_filename.strip() == "":
        raise HTTPException(status_code=400, detail="主LaTeX文件名不能为空")
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            logger.info(f"创建临时目录: {temp_path}")
            
            # 解压文件
            extract_path = temp_path / "extracted"
            extract_path.mkdir()
            
            # 使用通用解压函数
            extracted_file_names = await ppt_generator._extract_archive(archive_file, extract_path)
            
            # 列出解压后的文件
            extracted_files = []
            for file_path in extract_path.rglob('*'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(extract_path))
                    extracted_files.append(relative_path)
            
            logger.info(f"解压完成，共 {len(extracted_files)} 个文件:")
            for file in extracted_files[:10]:  # 只记录前10个文件
                logger.info(f"  - {file}")
            if len(extracted_files) > 10:
                logger.info(f"  ... 还有 {len(extracted_files) - 10} 个文件")
            
            # 查找指定的LaTeX文件
            tex_file_path = None
            target_file = main_tex_filename.strip()
            
            # 精确匹配
            for file_path in extract_path.rglob('*'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(extract_path))
                    if relative_path == target_file:
                        tex_file_path = file_path
                        break
            
            # 如果精确匹配失败，尝试忽略大小写匹配
            if not tex_file_path:
                for file_path in extract_path.rglob('*'):
                    if file_path.is_file():
                        relative_path = str(file_path.relative_to(extract_path))
                        if relative_path.lower() == target_file.lower():
                            tex_file_path = file_path
                            logger.info(f"找到文件（忽略大小写）: {relative_path}")
                            break
            
            # 如果还是找不到，尝试只匹配文件名（忽略路径）
            if not tex_file_path:
                target_filename = Path(target_file).name
                for file_path in extract_path.rglob('*'):
                    if file_path.is_file() and file_path.name == target_filename:
                        tex_file_path = file_path
                        logger.info(f"找到文件（仅匹配文件名）: {file_path.relative_to(extract_path)}")
                        break
            
            if not tex_file_path:
                # 列出所有tex文件供参考
                tex_files = [str(f.relative_to(extract_path)) for f in extract_path.rglob('*.tex')]
                logger.error(f"未找到文件 '{target_file}'，可用的tex文件: {tex_files}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"在压缩文件中未找到指定的LaTeX文件: {target_file}。可用的tex文件: {tex_files}"
                )
            
            logger.info(f"找到LaTeX文件: {tex_file_path}")
            
            # 读取LaTeX文件内容
            try:
                with open(tex_file_path, 'r', encoding='utf-8') as f:
                    latex_content = f.read()
                logger.info(f"成功读取LaTeX内容: {len(latex_content)} 字符")
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                logger.warning("UTF-8解码失败，尝试latin-1编码")
                try:
                    with open(tex_file_path, 'r', encoding='latin-1') as f:
                        latex_content = f.read()
                    logger.info(f"使用latin-1编码读取成功: {len(latex_content)} 字符")
                except Exception as e:
                    logger.error(f"读取文件内容失败: {e}")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"无法读取LaTeX文件内容: {str(e)}"
                    )
            
            result = {
                "success": True,
                "content": latex_content,
                "filename": main_tex_filename,
                "content_length": len(latex_content),
                "extracted_files_count": len(extracted_files)
            }
            
            logger.info("LaTeX内容提取成功完成")
            return result
            
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"提取LaTeX内容时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提取失败: {str(e)}")


@app.post("/generate_beamer_from_project")
async def generate_beamer_from_project(
    archive_file: UploadFile = File(...),
    beamer_content: str = Form(...),
    title: Optional[str] = Form(None),
    main_tex_filename: str = Form(...)
) -> Dict[str, Any]:
    """
    使用生成的Beamer代码和项目资源文件编译PDF
    
    Args:
        archive_file: 包含资源文件的压缩文件
        beamer_content: AI生成的Beamer LaTeX代码
        title: 演示文稿标题
        main_tex_filename: 原始主LaTeX文件名（用于识别）
        
    Returns:
        Dict[str, Any]: 编译结果
    """
    filename = archive_file.filename.lower()
    if not ppt_generator._is_supported_archive(filename):
        raise HTTPException(status_code=400, detail="请上传ZIP、TAR.GZ、TGZ或GZ格式的文件")
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 解压文件
            extract_path = temp_path / "extracted"
            extract_path.mkdir()
            
            # 使用通用解压函数
            extracted_file_names = await ppt_generator._extract_archive(archive_file, extract_path)
            
            # 创建模拟的UploadFile对象列表（排除原始主tex文件）
            project_files = []
            for file_path in extract_path.rglob('*'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(extract_path))
                    
                    # 跳过原始主tex文件，我们会用AI生成的Beamer代码替换
                    if relative_path == main_tex_filename:
                        continue
                    
                    # 创建模拟的UploadFile对象
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # 创建临时UploadFile
                    mock_file = UploadFile(
                        filename=relative_path,
                        file=BytesIO(file_content)
                    )
                    project_files.append(mock_file)
            
            # 使用AI生成的Beamer代码和项目资源编译PDF
            pdf_path = await ppt_generator._compile_beamer_with_resources(
                beamer_content, project_files, main_tex_filename, title or "presentation"
            )
            
            return {
                "success": True,
                "pdf_path": str(pdf_path),
                "title": title,
                "main_file": main_tex_filename,
                "resource_files_count": len(project_files)
            }
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的ZIP文件")
    except tarfile.TarError:
        raise HTTPException(status_code=400, detail="无效的TAR.GZ文件")
    except Exception as e:
        logger.error(f"编译Beamer PDF失败: {e}")
        raise HTTPException(status_code=500, detail=f"编译失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动 PPT 生成器服务...")
    uvicorn.run(app, host="0.0.0.0", port=8002) 