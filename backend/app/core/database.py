"""
数据库连接和初始化模块
使用 SQLAlchemy 2.0 异步 ORM
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from app.core.config import settings


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类
    """
    pass


# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 禁用数据库SQL日志
    future=True,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    获取数据库会话
    用于依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库
    创建所有表
    """
    try:
        # 导入所有模型以确保它们被注册
        from app.models import task, user  # noqa
        
        async with engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise e


async def close_db() -> None:
    """
    关闭数据库连接
    """
    await engine.dispose()
    logger.info("数据库连接已关闭") 