#!/usr/bin/env python3
"""
Database setup script for the FFXIV Discord bot.
Run this script to create all necessary database tables.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.db import init_db_connection, create_tables
from utils.logging import setup_logging
from config import load_config

# Load configuration
config = load_config()

# Set up logging
logger = setup_logging(config.logging_level)

async def setup_database():
    """Set up the database schema."""
    try:
        logger.info("Initializing database connection...")
        await init_db_connection()
        
        logger.info("Creating database tables...")
        await create_tables()
        
        logger.info("Database setup complete!")
        
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise
    
if __name__ == "__main__":
    try:
        asyncio.run(setup_database())
    except KeyboardInterrupt:
        logger.info("Database setup interrupted")
    except Exception as e:
        logger.error(f"Failed to set up database: {e}")
        sys.exit(1)