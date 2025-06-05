"""
日程提醒 MCP 服务
使用 FastMCP 框架提供日程管理和提醒功能
"""

import os
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import time
import threading


@dataclass
class ScheduleEvent:
    """日程事件数据类"""
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    reminder_minutes: int = 15
    repeat_type: str = "none"  # none, daily, weekly, monthly
    priority: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, completed, cancelled
    created_at: datetime = None


class ScheduleCreateRequest(BaseModel):
    """创建日程请求模型"""
    title: str
    description: Optional[str] = ""
    start_time: str  # ISO格式时间字符串
    end_time: Optional[str] = None
    reminder_minutes: int = 15
    repeat_type: str = "none"
    priority: str = "medium"


class ScheduleUpdateRequest(BaseModel):
    """更新日程请求模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reminder_minutes: Optional[int] = None
    repeat_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class ReminderRequest(BaseModel):
    """提醒设置请求模型"""
    event_id: str
    reminder_type: str = "notification"  # notification, email, sound
    advance_minutes: int = 15


class ScheduleManager:
    """
    日程管理器类
    负责日程的CRUD操作、提醒和日历功能
    """
    
    def __init__(self):
        self.db_path = Path("./schedule.db")
        self.reminders = {}  # 存储提醒任务
        self.reminder_thread = None
        self.running = False
        
        # 初始化数据库
        self._init_database()
        
        # 启动提醒服务
        self._start_reminder_service()
    
    def _init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建日程表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    reminder_minutes INTEGER DEFAULT 15,
                    repeat_type TEXT DEFAULT 'none',
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 创建提醒表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    reminder_type TEXT NOT NULL,
                    advance_minutes INTEGER NOT NULL,
                    triggered INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES schedules (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("数据库初始化成功")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise e
    
    def _start_reminder_service(self):
        """启动提醒服务后台线程"""
        self.running = True
        self.reminder_thread = threading.Thread(target=self._reminder_worker, daemon=True)
        self.reminder_thread.start()
        logger.info("提醒服务已启动")
    
    def _reminder_worker(self):
        """提醒服务工作线程"""
        while self.running:
            try:
                self._check_and_send_reminders()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"提醒服务错误: {e}")
                time.sleep(30)  # 出错时等待30秒后重试
    
    def _check_and_send_reminders(self):
        """检查并发送提醒"""
        try:
            now = datetime.now()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询需要提醒的事件
            cursor.execute('''
                SELECT s.id, s.title, s.description, s.start_time, s.reminder_minutes
                FROM schedules s
                WHERE s.status = 'pending'
                AND datetime(s.start_time, '-' || s.reminder_minutes || ' minutes') <= ?
                AND s.id NOT IN (
                    SELECT event_id FROM reminders WHERE triggered = 1
                )
            ''', (now.isoformat(),))
            
            events = cursor.fetchall()
            
            for event in events:
                event_id, title, description, start_time_str, reminder_minutes = event
                
                # 发送提醒
                self._send_reminder(event_id, title, description, start_time_str)
                
                # 标记为已提醒
                cursor.execute('''
                    INSERT OR REPLACE INTO reminders 
                    (id, event_id, reminder_type, advance_minutes, triggered, created_at)
                    VALUES (?, ?, 'notification', ?, 1, ?)
                ''', (f"{event_id}_reminder", event_id, reminder_minutes, now.isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"检查提醒失败: {e}")
    
    def _send_reminder(self, event_id: str, title: str, description: str, start_time_str: str):
        """发送提醒通知"""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            
            reminder_message = {
                "type": "schedule_reminder",
                "event_id": event_id,
                "title": title,
                "description": description,
                "start_time": start_time_str,
                "message": f"提醒：{title} 即将开始",
                "timestamp": datetime.now().isoformat()
            }
            
            # 这里可以扩展多种提醒方式
            logger.info(f"📅 日程提醒: {title} - {description}")
            
            # 可以在这里添加推送到前端的逻辑
            # 比如通过WebSocket或者SSE推送给前端
            
        except Exception as e:
            logger.error(f"发送提醒失败: {e}")
    
    async def create_schedule(self, request: ScheduleCreateRequest) -> Dict[str, Any]:
        """创建日程"""
        try:
            import uuid
            
            event_id = str(uuid.uuid4())
            now = datetime.now()
            
            # 解析时间
            start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
            end_time = None
            if request.end_time:
                end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
            
            # 验证时间
            if start_time <= now:
                raise ValueError("开始时间必须是未来时间")
            
            if end_time and end_time <= start_time:
                raise ValueError("结束时间必须晚于开始时间")
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO schedules 
                (id, title, description, start_time, end_time, reminder_minutes, 
                 repeat_type, priority, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, request.title, request.description,
                start_time.isoformat(), end_time.isoformat() if end_time else None,
                request.reminder_minutes, request.repeat_type, request.priority,
                "pending", now.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            result = {
                "success": True,
                "event_id": event_id,
                "title": request.title,
                "start_time": start_time.isoformat(),
                "message": "日程创建成功"
            }
            
            logger.info(f"日程创建成功: {request.title} at {start_time}")
            return result
            
        except Exception as e:
            logger.error(f"创建日程失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_schedules(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取日程列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建查询条件
            where_conditions = []
            params = []
            
            if start_date:
                where_conditions.append("start_time >= ?")
                params.append(start_date)
            
            if end_date:
                where_conditions.append("start_time <= ?")
                params.append(end_date)
            
            if status:
                where_conditions.append("status = ?")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            query = f'''
                SELECT id, title, description, start_time, end_time, 
                       reminder_minutes, repeat_type, priority, status, created_at
                FROM schedules 
                {where_clause}
                ORDER BY start_time
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            schedules = []
            for row in rows:
                schedule_data = {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "start_time": row[3],
                    "end_time": row[4],
                    "reminder_minutes": row[5],
                    "repeat_type": row[6],
                    "priority": row[7],
                    "status": row[8],
                    "created_at": row[9]
                }
                schedules.append(schedule_data)
            
            conn.close()
            
            return {
                "success": True,
                "schedules": schedules,
                "count": len(schedules)
            }
            
        except Exception as e:
            logger.error(f"获取日程列表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def update_schedule(self, event_id: str, request: ScheduleUpdateRequest) -> Dict[str, Any]:
        """更新日程"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查日程是否存在
            cursor.execute("SELECT id FROM schedules WHERE id = ?", (event_id,))
            if not cursor.fetchone():
                raise ValueError("日程不存在")
            
            # 构建更新语句
            update_fields = []
            params = []
            
            if request.title is not None:
                update_fields.append("title = ?")
                params.append(request.title)
            
            if request.description is not None:
                update_fields.append("description = ?")
                params.append(request.description)
            
            if request.start_time is not None:
                start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
                update_fields.append("start_time = ?")
                params.append(start_time.isoformat())
            
            if request.end_time is not None:
                end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
                update_fields.append("end_time = ?")
                params.append(end_time.isoformat())
            
            if request.reminder_minutes is not None:
                update_fields.append("reminder_minutes = ?")
                params.append(request.reminder_minutes)
            
            if request.repeat_type is not None:
                update_fields.append("repeat_type = ?")
                params.append(request.repeat_type)
            
            if request.priority is not None:
                update_fields.append("priority = ?")
                params.append(request.priority)
            
            if request.status is not None:
                update_fields.append("status = ?")
                params.append(request.status)
            
            if not update_fields:
                raise ValueError("没有提供更新字段")
            
            params.append(event_id)
            
            query = f"UPDATE schedules SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "event_id": event_id,
                "message": "日程更新成功"
            }
            
        except Exception as e:
            logger.error(f"更新日程失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def delete_schedule(self, event_id: str) -> Dict[str, Any]:
        """删除日程"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查日程是否存在
            cursor.execute("SELECT id FROM schedules WHERE id = ?", (event_id,))
            if not cursor.fetchone():
                raise ValueError("日程不存在")
            
            # 删除相关提醒
            cursor.execute("DELETE FROM reminders WHERE event_id = ?", (event_id,))
            
            # 删除日程
            cursor.execute("DELETE FROM schedules WHERE id = ?", (event_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "event_id": event_id,
                "message": "日程删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除日程失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_calendar_data(self, year: int, month: int) -> Dict[str, Any]:
        """获取日历数据"""
        try:
            from calendar import monthrange
            
            # 获取月份的第一天和最后一天
            first_day = datetime(year, month, 1)
            last_day_num = monthrange(year, month)[1]
            last_day = datetime(year, month, last_day_num, 23, 59, 59)
            
            # 获取该月的所有日程
            schedules_result = await self.get_schedules(
                start_date=first_day.isoformat(),
                end_date=last_day.isoformat()
            )
            
            if not schedules_result.get("success"):
                raise Exception("获取日程数据失败")
            
            schedules = schedules_result.get("schedules", [])
            
            # 按日期组织数据
            calendar_data = {}
            for schedule in schedules:
                start_time = datetime.fromisoformat(schedule["start_time"])
                date_key = start_time.strftime("%Y-%m-%d")
                
                if date_key not in calendar_data:
                    calendar_data[date_key] = []
                
                calendar_data[date_key].append({
                    "id": schedule["id"],
                    "title": schedule["title"],
                    "start_time": schedule["start_time"],
                    "priority": schedule["priority"],
                    "status": schedule["status"]
                })
            
            return {
                "success": True,
                "year": year,
                "month": month,
                "calendar_data": calendar_data,
                "total_events": len(schedules)
            }
            
        except Exception as e:
            logger.error(f"获取日历数据失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def stop_reminder_service(self):
        """停止提醒服务"""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=5)
        logger.info("提醒服务已停止")


# 创建 FastAPI 应用
app = FastAPI(
    title="Schedule Reminder Service", 
    description="日程提醒服务",
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

# 创建日程管理器实例
schedule_manager = ScheduleManager()


@app.get("/")
async def root():
    """服务健康检查"""
    return {
        "service": "Schedule Reminder",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    return {
        "service": "Schedule Reminder",
        "status": "running",
        "reminder_service_running": schedule_manager.running,
        "db_path": str(schedule_manager.db_path),
        "db_exists": schedule_manager.db_path.exists()
    }


@app.post("/create_schedule")
async def create_schedule(request: ScheduleCreateRequest) -> Dict[str, Any]:
    """
    创建日程
    
    Args:
        request: 日程创建请求
        
    Returns:
        Dict[str, Any]: 创建结果
    """
    result = await schedule_manager.create_schedule(request)
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "创建日程失败"))
    
    return result


@app.get("/schedules")
async def get_schedules(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取日程列表
    
    Args:
        start_date: 开始日期 (ISO格式)
        end_date: 结束日期 (ISO格式)
        status: 状态过滤
        
    Returns:
        Dict[str, Any]: 日程列表
    """
    result = await schedule_manager.get_schedules(start_date, end_date, status)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "获取日程失败"))
    
    return result


@app.put("/schedules/{event_id}")
async def update_schedule(event_id: str, request: ScheduleUpdateRequest) -> Dict[str, Any]:
    """
    更新日程
    
    Args:
        event_id: 事件ID
        request: 更新请求
        
    Returns:
        Dict[str, Any]: 更新结果
    """
    result = await schedule_manager.update_schedule(event_id, request)
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "更新日程失败"))
    
    return result


@app.delete("/schedules/{event_id}")
async def delete_schedule(event_id: str) -> Dict[str, Any]:
    """
    删除日程
    
    Args:
        event_id: 事件ID
        
    Returns:
        Dict[str, Any]: 删除结果
    """
    result = await schedule_manager.delete_schedule(event_id)
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "删除日程失败"))
    
    return result


@app.get("/calendar/{year}/{month}")
async def get_calendar_data(year: int, month: int) -> Dict[str, Any]:
    """
    获取日历数据
    
    Args:
        year: 年份
        month: 月份
        
    Returns:
        Dict[str, Any]: 日历数据
    """
    result = await schedule_manager.get_calendar_data(year, month)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "获取日历数据失败"))
    
    return result


# 应用关闭时清理资源
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理工作"""
    schedule_manager.stop_reminder_service()


if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动日程提醒服务...")
    uvicorn.run(app, host="0.0.0.0", port=8004) 