"""
文件上传 API 端点
提供文件上传和管理功能
"""

import os
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from loguru import logger

from app.core.config import settings

# 创建路由器
router = APIRouter()


@router.post("/", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    上传文件
    """
    try:
        # 检查文件大小
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE} bytes)"
            )
        
        # 创建上传目录
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # 生成唯一文件名，正确处理复合扩展名如.tar.gz
        def get_full_extension(filename: str) -> str:
            """获取完整的文件扩展名，包括.tar.gz等复合扩展名"""
            if filename.lower().endswith('.tar.gz'):
                return '.tar.gz'
            elif filename.lower().endswith('.tar.bz2'):
                return '.tar.bz2'
            elif filename.lower().endswith('.tar.xz'):
                return '.tar.xz'
            else:
                return Path(filename).suffix
        
        file_extension = get_full_extension(file.filename)
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"文件上传成功: {file_path}")
        
        return {
            "success": True,
            "filename": unique_filename,
            "original_filename": file.filename,
            "path": str(file_path),
            "size": file.size,
            "content_type": file.content_type,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail="文件上传失败")


@router.get("/list", response_model=Dict[str, Any])
async def list_uploaded_files() -> Dict[str, Any]:
    """
    列出已上传的文件
    """
    try:
        upload_dir = Path(settings.UPLOAD_DIR)
        
        if not upload_dir.exists():
            return {"files": [], "total": 0}
        
        files = []
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime,
                })
        
        # 按修改时间排序
        files.sort(key=lambda x: x["modified_at"], reverse=True)
        
        return {
            "files": files,
            "total": len(files),
        }
    
    except Exception as e:
        logger.error(f"列出文件失败: {e}")
        raise HTTPException(status_code=500, detail="列出文件失败")


@router.delete("/{filename}", response_model=Dict[str, Any])
async def delete_file(filename: str) -> Dict[str, Any]:
    """
    删除上传的文件
    """
    try:
        file_path = Path(settings.UPLOAD_DIR) / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_path.unlink()
        
        logger.info(f"文件删除成功: {file_path}")
        
        return {
            "success": True,
            "message": "文件删除成功",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail="删除文件失败") 