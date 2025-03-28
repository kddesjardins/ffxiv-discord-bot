"""
Database connection utilities for the FFXIV Discord bot.
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine

from config import load_config
from models.base import Base

# Logger
logger = logging.getLogger("ffxiv_bot")

# Global engine reference
_engine: Optional[AsyncEngine] = None
_async_session_factory = None

async def init_db_connection():
    """Initialize database connection."""
    global _engine, _async_session_factory
    
    config = load_config()
    
    # Create engine
    try:
        logger.info("Initializing database connection...")
        
        # Convert SQLAlchemy URL format to asyncpg format
        db_url = config.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
        _engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for SQL query logging
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,  # Recycle connections after 30 minutes
        )
        
        # Create session factory
        _async_session_factory = sessionmaker(
            _engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # Verify connection using SQLAlchemy core with text()
        async with _engine.begin() as conn:
            # Use a text() query to check connection
            await conn.execute(text("SELECT 1"))
            
        logger.info("Database connection established successfully")
        
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

async def close_db_connection():
    """Close database connection."""
    global _engine
    
    if _engine:
        logger.info("Closing database connection...")
        await _engine.dispose()
        _engine = None
        logger.info("Database connection closed")

@asynccontextmanager
async def get_db_session():
    """Get a database session as a context manager."""
    global _async_session_factory
    
    if not _async_session_factory:
        raise RuntimeError("Database not initialized. Call init_db_connection first.")
    
    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()

async def create_tables():
    """Create all tables in the database."""
    global _engine
    
    if not _engine:
        raise RuntimeError("Database not initialized. Call init_db_connection first.")
    
    # Import all models to ensure they're registered with Base
    import models.character
    import models.group
    import models.progress
    
    async with _engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")

async def perform_maintenance():
    """Perform routine database maintenance."""
    global _engine
    
    if not _engine:
        return
    
    logger.info("Performing database maintenance...")
    
    try:
        async with _engine.begin() as conn:
            # Run VACUUM ANALYZE to update statistics and reclaim space
            await conn.execute(text("VACUUM ANALYZE"))
        
        logger.info("Database maintenance completed")
        
    except Exception as e:
        logger.error(f"Error during database maintenance: {e}")