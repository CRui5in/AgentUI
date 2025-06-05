"""
API 文档生成器 MCP 服务
使用 FastMCP 框架提供 API 文档生成功能
"""

import os
import ast
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import re

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger
import requests


class DocGenerateRequest(BaseModel):
    """文档生成请求模型"""
    project_name: str
    source_type: str  # local, github, upload
    source_data: Dict[str, Any]  # 根据源类型的不同数据
    language: str = "auto"
    output_format: str = "markdown"  # markdown, html, pdf
    include_private: bool = False
    include_internal: bool = False
    include_tests: bool = False
    include_examples: bool = True
    generate_openapi: bool = True
    generate_postman: bool = False
    doc_style: str = "detailed"  # brief, detailed, comprehensive


class CodeAnalyzeRequest(BaseModel):
    """代码分析请求模型"""
    project_name: str
    source_type: str
    source_data: Dict[str, Any]
    language: str = "auto"
    include_private: bool = False
    include_internal: bool = False
    include_tests: bool = False


class APIDocGenerator:
    """
    API 文档生成器类
    支持多种编程语言的 API 文档生成
    """
    
    def __init__(self):
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = Path("./temp")
        self.temp_dir.mkdir(exist_ok=True)
        
    async def analyze_codebase(
        self,
        project_name: str,
        source_type: str,
        source_data: Dict[str, Any],
        language: str = "auto",
        include_private: bool = False,
        include_internal: bool = False,
        include_tests: bool = False
    ) -> Dict[str, Any]:
        """
        分析代码库结构
        
        Args:
            project_name: 项目名称
            source_type: 源类型
            source_data: 源数据
            language: 编程语言
            include_private: 是否包含私有方法
            include_internal: 是否包含内部API
            include_tests: 是否包含测试代码
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            logger.info(f"开始分析代码库: {project_name}")
            
            # 获取代码文件
            source_path = await self._prepare_source_code(source_type, source_data)
            
            # 检测编程语言
            if language == "auto":
                language = self._detect_language(source_path)
            
            # 分析代码结构
            analysis_result = await self._analyze_source_code(
                source_path, language, include_private, include_internal, include_tests
            )
            
            result = {
                "success": True,
                "project_name": project_name,
                "language": language,
                "source_type": source_type,
                "analysis": analysis_result
            }
            
            logger.info(f"代码库分析完成: {project_name}")
            return result
            
        except Exception as e:
            logger.error(f"代码库分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def generate_documentation(
        self,
        request: DocGenerateRequest
    ) -> Dict[str, Any]:
        """
        生成 API 文档
        
        Args:
            request: 文档生成请求
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            logger.info(f"开始生成文档: {request.project_name}")
            
            # 先分析代码库
            analysis_result = await self.analyze_codebase(
                request.project_name,
                request.source_type,
                request.source_data,
                request.language,
                request.include_private,
                request.include_internal,
                request.include_tests
            )
            
            if not analysis_result.get("success"):
                raise Exception(f"代码分析失败: {analysis_result.get('error')}")
            
            # 生成文档内容
            doc_content = await self._generate_doc_content(
                analysis_result["analysis"],
                request.project_name,
                request.doc_style,
                request.include_examples
            )
            
            # 保存文档文件
            doc_path = await self._save_documentation(
                doc_content,
                request.project_name,
                request.output_format
            )
            
            # 生成额外格式
            extra_files = []
            if request.generate_openapi:
                openapi_path = await self._generate_openapi_spec(
                    analysis_result["analysis"],
                    request.project_name
                )
                if openapi_path:
                    extra_files.append(openapi_path)
            
            if request.generate_postman:
                postman_path = await self._generate_postman_collection(
                    analysis_result["analysis"],
                    request.project_name
                )
                if postman_path:
                    extra_files.append(postman_path)
            
            result = {
                "success": True,
                "project_name": request.project_name,
                "doc_path": str(doc_path),
                "output_format": request.output_format,
                "extra_files": [str(f) for f in extra_files],
                "analysis_summary": {
                    "total_files": len(analysis_result["analysis"].get("files", [])),
                    "total_functions": len(analysis_result["analysis"].get("functions", [])),
                    "total_classes": len(analysis_result["analysis"].get("classes", []))
                }
            }
            
            logger.info(f"文档生成成功: {doc_path}")
            return result
            
        except Exception as e:
            logger.error(f"文档生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _prepare_source_code(self, source_type: str, source_data: Dict[str, Any]) -> Path:
        """准备源代码"""
        if source_type == "local":
            path = Path(source_data.get("path", ""))
            if not path.exists():
                raise Exception(f"本地路径不存在: {path}")
            return path
            
        elif source_type == "github":
            github_url = source_data.get("github_url", "")
            return await self._clone_github_repo(github_url)
            
        elif source_type == "upload":
            uploaded_files = source_data.get("uploaded_files", [])
            return await self._extract_uploaded_files(uploaded_files)
            
        else:
            raise Exception(f"不支持的源类型: {source_type}")
    
    async def _clone_github_repo(self, github_url: str) -> Path:
        """克隆GitHub仓库"""
        try:
            repo_name = github_url.split("/")[-1].replace(".git", "")
            clone_path = self.temp_dir / f"github_{repo_name}"
            
            # 删除已存在的目录
            if clone_path.exists():
                shutil.rmtree(clone_path)
            
            # 克隆仓库
            result = subprocess.run([
                "git", "clone", "--depth", "1", github_url, str(clone_path)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Git克隆失败: {result.stderr}")
            
            return clone_path
            
        except Exception as e:
            raise Exception(f"克隆GitHub仓库失败: {e}")
    
    async def _extract_uploaded_files(self, uploaded_files: List[str]) -> Path:
        """提取上传的文件"""
        # 这里应该从后端获取上传的文件，现在简化处理
        extract_path = self.temp_dir / "uploaded_project"
        extract_path.mkdir(exist_ok=True)
        return extract_path
    
    def _detect_language(self, source_path: Path) -> str:
        """检测编程语言"""
        extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.cpp': 'cpp',
            '.c': 'c'
        }
        
        # 统计文件扩展名
        ext_count = {}
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in extensions:
                    ext_count[ext] = ext_count.get(ext, 0) + 1
        
        if not ext_count:
            return "unknown"
        
        # 返回最常见的语言
        most_common_ext = max(ext_count, key=ext_count.get)
        return extensions.get(most_common_ext, "unknown")
    
    async def _analyze_source_code(
        self,
        source_path: Path,
        language: str,
        include_private: bool,
        include_internal: bool,
        include_tests: bool
    ) -> Dict[str, Any]:
        """分析源代码结构"""
        if language == "python":
            return await self._analyze_python_code(source_path, include_private, include_internal, include_tests)
        elif language in ["javascript", "typescript"]:
            return await self._analyze_js_code(source_path, include_private, include_internal, include_tests)
        else:
            return await self._analyze_generic_code(source_path, include_private, include_internal, include_tests)
    
    async def _analyze_python_code(
        self,
        source_path: Path,
        include_private: bool,
        include_internal: bool,
        include_tests: bool
    ) -> Dict[str, Any]:
        """分析Python代码"""
        files = []
        classes = []
        functions = []
        
        for py_file in source_path.rglob("*.py"):
            # 跳过测试文件（如果不包含测试）
            if not include_tests and ("test" in py_file.name.lower() or "tests" in str(py_file).lower()):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析AST
                tree = ast.parse(content)
                
                file_info = {
                    "path": str(py_file.relative_to(source_path)),
                    "size": py_file.stat().st_size,
                    "classes": [],
                    "functions": []
                }
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 跳过私有类（如果不包含私有）
                        if not include_private and node.name.startswith('_'):
                            continue
                        
                        class_info = {
                            "name": node.name,
                            "file": str(py_file.relative_to(source_path)),
                            "line": node.lineno,
                            "docstring": ast.get_docstring(node),
                            "methods": [],
                            "is_private": node.name.startswith('_')
                        }
                        
                        # 分析方法
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                if not include_private and item.name.startswith('_'):
                                    continue
                                
                                method_info = {
                                    "name": item.name,
                                    "line": item.lineno,
                                    "docstring": ast.get_docstring(item),
                                    "args": [arg.arg for arg in item.args.args],
                                    "is_private": item.name.startswith('_')
                                }
                                class_info["methods"].append(method_info)
                        
                        classes.append(class_info)
                        file_info["classes"].append(class_info)
                    
                    elif isinstance(node, ast.FunctionDef):
                        # 跳过私有函数（如果不包含私有）
                        if not include_private and node.name.startswith('_'):
                            continue
                        
                        func_info = {
                            "name": node.name,
                            "file": str(py_file.relative_to(source_path)),
                            "line": node.lineno,
                            "docstring": ast.get_docstring(node),
                            "args": [arg.arg for arg in node.args.args],
                            "is_private": node.name.startswith('_')
                        }
                        functions.append(func_info)
                        file_info["functions"].append(func_info)
                
                files.append(file_info)
                
            except Exception as e:
                logger.warning(f"解析Python文件失败 {py_file}: {e}")
                continue
        
        return {
            "language": "python",
            "files": files,
            "classes": classes,
            "functions": functions,
            "summary": {
                "total_files": len(files),
                "total_classes": len(classes),
                "total_functions": len(functions)
            }
        }
    
    async def _analyze_js_code(
        self,
        source_path: Path,
        include_private: bool,
        include_internal: bool,
        include_tests: bool
    ) -> Dict[str, Any]:
        """分析JavaScript/TypeScript代码"""
        files = []
        functions = []
        classes = []
        
        patterns = ["*.js", "*.ts", "*.jsx", "*.tsx"]
        
        for pattern in patterns:
            for js_file in source_path.rglob(pattern):
                if not include_tests and ("test" in js_file.name.lower() or "spec" in js_file.name.lower()):
                    continue
                
                try:
                    with open(js_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    file_info = {
                        "path": str(js_file.relative_to(source_path)),
                        "size": js_file.stat().st_size,
                        "functions": [],
                        "classes": []
                    }
                    
                    # 简单的正则表达式解析（实际项目中应该使用AST解析器）
                    
                    # 查找函数定义
                    func_patterns = [
                        r'function\s+(\w+)\s*\(',  # function name()
                        r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>'  # const name = () =>
                    ]
                    
                    for pattern in func_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            func_name = match.group(1)
                            if not include_private and func_name.startswith('_'):
                                continue
                            
                            func_info = {
                                "name": func_name,
                                "file": str(js_file.relative_to(source_path)),
                                "type": "function",
                                "is_private": func_name.startswith('_')
                            }
                            functions.append(func_info)
                            file_info["functions"].append(func_info)
                    
                    # 查找类定义
                    class_matches = re.finditer(r'class\s+(\w+)', content)
                    for match in class_matches:
                        class_name = match.group(1)
                        if not include_private and class_name.startswith('_'):
                            continue
                        
                        class_info = {
                            "name": class_name,
                            "file": str(js_file.relative_to(source_path)),
                            "type": "class",
                            "is_private": class_name.startswith('_')
                        }
                        classes.append(class_info)
                        file_info["classes"].append(class_info)
                    
                    files.append(file_info)
                    
                except Exception as e:
                    logger.warning(f"解析JS文件失败 {js_file}: {e}")
                    continue
        
        return {
            "language": "javascript",
            "files": files,
            "classes": classes,
            "functions": functions,
            "summary": {
                "total_files": len(files),
                "total_classes": len(classes),
                "total_functions": len(functions)
            }
        }
    
    async def _analyze_generic_code(
        self,
        source_path: Path,
        include_private: bool,
        include_internal: bool,
        include_tests: bool
    ) -> Dict[str, Any]:
        """分析通用代码（其他语言）"""
        files = []
        
        # 收集所有代码文件
        code_extensions = {'.java', '.cs', '.go', '.rs', '.php', '.rb', '.cpp', '.c', '.h'}
        
        for file_path in source_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in code_extensions:
                if not include_tests and "test" in file_path.name.lower():
                    continue
                
                file_info = {
                    "path": str(file_path.relative_to(source_path)),
                    "size": file_path.stat().st_size,
                    "extension": file_path.suffix
                }
                files.append(file_info)
        
        return {
            "language": "generic",
            "files": files,
            "classes": [],
            "functions": [],
            "summary": {
                "total_files": len(files),
                "total_classes": 0,
                "total_functions": 0
            }
        }
    
    async def _generate_doc_content(
        self,
        analysis: Dict[str, Any],
        project_name: str,
        doc_style: str,
        include_examples: bool
    ) -> str:
        """生成文档内容"""
        
        # 构建Markdown文档
        doc_lines = [
            f"# {project_name} API 文档",
            "",
            "## 项目概述",
            "",
            f"- **编程语言**: {analysis.get('language', 'Unknown')}",
            f"- **文件总数**: {analysis['summary']['total_files']}",
            f"- **类总数**: {analysis['summary']['total_classes']}",
            f"- **函数总数**: {analysis['summary']['total_functions']}",
            ""
        ]
        
        # 添加目录
        if doc_style in ["detailed", "comprehensive"]:
            doc_lines.extend([
                "## 目录",
                "",
                "- [项目概述](#项目概述)",
                "- [文件结构](#文件结构)",
                "- [API 参考](#api-参考)",
            ])
            
            if analysis['summary']['total_classes'] > 0:
                doc_lines.append("  - [类](#类)")
            
            if analysis['summary']['total_functions'] > 0:
                doc_lines.append("  - [函数](#函数)")
            
            if include_examples:
                doc_lines.append("- [使用示例](#使用示例)")
            
            doc_lines.append("")
        
        # 文件结构
        doc_lines.extend([
            "## 文件结构",
            "",
            "```"
        ])
        
        for file_info in analysis.get("files", []):
            doc_lines.append(f"{file_info['path']} ({file_info['size']} bytes)")
        
        doc_lines.extend(["```", ""])
        
        # API 参考
        doc_lines.extend([
            "## API 参考",
            ""
        ])
        
        # 类文档
        if analysis['summary']['total_classes'] > 0:
            doc_lines.extend([
                "### 类",
                ""
            ])
            
            for class_info in analysis.get("classes", []):
                doc_lines.extend([
                    f"#### {class_info['name']}",
                    "",
                    f"**文件**: `{class_info['file']}`",
                    ""
                ])
                
                if class_info.get("docstring"):
                    doc_lines.extend([
                        "**描述**:",
                        "",
                        class_info["docstring"],
                        ""
                    ])
                
                # 方法
                if class_info.get("methods"):
                    doc_lines.extend([
                        "**方法**:",
                        ""
                    ])
                    
                    for method in class_info["methods"]:
                        args_str = ", ".join(method.get("args", []))
                        doc_lines.append(f"- `{method['name']}({args_str})`")
                        
                        if method.get("docstring") and doc_style == "comprehensive":
                            doc_lines.append(f"  - {method['docstring']}")
                    
                    doc_lines.append("")
        
        # 函数文档
        if analysis['summary']['total_functions'] > 0:
            doc_lines.extend([
                "### 函数",
                ""
            ])
            
            for func_info in analysis.get("functions", []):
                args_str = ", ".join(func_info.get("args", []))
                doc_lines.extend([
                    f"#### {func_info['name']}({args_str})",
                    "",
                    f"**文件**: `{func_info['file']}`",
                    ""
                ])
                
                if func_info.get("docstring"):
                    doc_lines.extend([
                        "**描述**:",
                        "",
                        func_info["docstring"],
                        ""
                    ])
        
        # 使用示例
        if include_examples:
            doc_lines.extend([
                "## 使用示例",
                "",
                "```python",
                "# 这里添加使用示例",
                "# 根据分析结果生成适当的示例代码",
                "```",
                ""
            ])
        
        # 生成时间
        from datetime import datetime
        doc_lines.extend([
            "---",
            f"*文档生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(doc_lines)
    
    async def _save_documentation(
        self,
        content: str,
        project_name: str,
        output_format: str
    ) -> Path:
        """保存文档"""
        safe_name = re.sub(r'[^\w\-_.]', '_', project_name)
        
        if output_format == "markdown":
            file_path = self.output_dir / f"{safe_name}_api_docs.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        elif output_format == "html":
            # 简单的Markdown到HTML转换
            html_content = self._markdown_to_html(content)
            file_path = self.output_dir / f"{safe_name}_api_docs.html"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        else:
            raise Exception(f"不支持的输出格式: {output_format}")
        
        return file_path
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """简单的Markdown到HTML转换"""
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='utf-8'>",
            "    <title>API Documentation</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 40px; }",
            "        h1, h2, h3, h4 { color: #333; }",
            "        code { background-color: #f4f4f4; padding: 2px 4px; }",
            "        pre { background-color: #f4f4f4; padding: 10px; overflow-x: auto; }",
            "    </style>",
            "</head>",
            "<body>"
        ]
        
        # 简单转换（实际项目中应该使用专门的Markdown解析器）
        lines = markdown_content.split('\n')
        in_code_block = False
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    html_lines.append('</pre>')
                    in_code_block = False
                else:
                    html_lines.append('<pre>')
                    in_code_block = True
            elif in_code_block:
                html_lines.append(line)
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('#### '):
                html_lines.append(f'<h4>{line[5:]}</h4>')
            elif line.strip() == '':
                html_lines.append('<br>')
            else:
                # 处理行内代码
                line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
                html_lines.append(f'<p>{line}</p>')
        
        html_lines.extend([
            "</body>",
            "</html>"
        ])
        
        return '\n'.join(html_lines)
    
    async def _generate_openapi_spec(self, analysis: Dict[str, Any], project_name: str) -> Optional[Path]:
        """生成OpenAPI规范文件"""
        try:
            # 这里是示例，实际应该根据代码分析结果生成
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": f"{project_name} API",
                    "version": "1.0.0",
                    "description": "Auto-generated API documentation"
                },
                "paths": {},
                "components": {
                    "schemas": {}
                }
            }
            
            # 根据分析结果添加路径和模式
            for func in analysis.get("functions", []):
                if "api" in func["name"].lower() or "route" in func["name"].lower():
                    path = f"/{func['name']}"
                    openapi_spec["paths"][path] = {
                        "get": {
                            "summary": func.get("docstring", f"Call {func['name']}"),
                            "responses": {
                                "200": {
                                    "description": "Success"
                                }
                            }
                        }
                    }
            
            safe_name = re.sub(r'[^\w\-_.]', '_', project_name)
            file_path = self.output_dir / f"{safe_name}_openapi.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
            
            return file_path
            
        except Exception as e:
            logger.warning(f"生成OpenAPI规范失败: {e}")
            return None
    
    async def _generate_postman_collection(self, analysis: Dict[str, Any], project_name: str) -> Optional[Path]:
        """生成Postman集合文件"""
        try:
            # 这里是示例，实际应该根据代码分析结果生成
            collection = {
                "info": {
                    "name": f"{project_name} API Collection",
                    "description": "Auto-generated Postman collection"
                },
                "item": []
            }
            
            # 根据分析结果添加请求
            for func in analysis.get("functions", []):
                if "api" in func["name"].lower() or "route" in func["name"].lower():
                    collection["item"].append({
                        "name": func["name"],
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": f"{{base_url}}/{func['name']}",
                                "host": ["{{base_url}}"],
                                "path": [func["name"]]
                            }
                        }
                    })
            
            safe_name = re.sub(r'[^\w\-_.]', '_', project_name)
            file_path = self.output_dir / f"{safe_name}_postman.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(collection, f, indent=2, ensure_ascii=False)
            
            return file_path
            
        except Exception as e:
            logger.warning(f"生成Postman集合失败: {e}")
            return None


# 创建 FastAPI 应用
app = FastAPI(
    title="API Doc Generator Service", 
    description="API文档生成器服务",
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

# 创建文档生成器实例
doc_generator = APIDocGenerator()


@app.get("/")
async def root():
    """服务健康检查"""
    return {
        "service": "API Doc Generator",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    return {
        "service": "API Doc Generator",
        "status": "running",
        "output_dir": str(doc_generator.output_dir),
        "output_dir_exists": doc_generator.output_dir.exists(),
        "temp_dir": str(doc_generator.temp_dir),
        "temp_dir_exists": doc_generator.temp_dir.exists()
    }


@app.post("/analyze_codebase")
async def analyze_codebase(request: CodeAnalyzeRequest) -> Dict[str, Any]:
    """
    分析代码库
    
    Args:
        request: 代码分析请求
        
    Returns:
        Dict[str, Any]: 分析结果
    """
    result = await doc_generator.analyze_codebase(
        project_name=request.project_name,
        source_type=request.source_type,
        source_data=request.source_data,
        language=request.language,
        include_private=request.include_private,
        include_internal=request.include_internal,
        include_tests=request.include_tests
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result)
    
    return result


@app.post("/generate_docs")
async def generate_docs(request: DocGenerateRequest) -> Dict[str, Any]:
    """
    生成API文档
    
    Args:
        request: 文档生成请求
        
    Returns:
        Dict[str, Any]: 生成结果
    """
    result = await doc_generator.generate_documentation(request)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result)
    
    return result


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载生成的文档文件
    
    Args:
        filename: 文件名
        
    Returns:
        FileResponse: 文档文件
    """
    file_path = doc_generator.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 根据文件扩展名确定媒体类型
    media_type = "application/octet-stream"
    if filename.endswith('.md'):
        media_type = "text/markdown"
    elif filename.endswith('.html'):
        media_type = "text/html"
    elif filename.endswith('.json'):
        media_type = "application/json"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动API文档生成器服务...")
    uvicorn.run(app, host="0.0.0.0", port=8005) 