"""
Logging configuration for the FFXIV Discord bot.
"""
import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

def setup_logging(level: int = logging.INFO, log_to_file: bool = False, 
                  log_file_path: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level
        log_to_file: Whether to log to a file
        log_file_path: Path to log file, if logging to file
        
    Returns:
        Logger instance for the bot
    """
    # Create logger
    logger = logging.getLogger("ffxiv_bot")
    logger.setLevel(level)
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file and log_file_path:
        # Ensure log directory exists
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler (10 files, 5MB each)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=5*1024*1024, backupCount=10
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    return logger

def get_logger() -> logging.Logger:
    """Get the bot's logger instance."""
    return logging.getLogger("ffxiv_bot")