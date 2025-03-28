"""
Configuration management for the FFXIV Discord bot.
Loads settings from environment variables with sensible defaults.
"""
import os
from dataclasses import dataclass
from typing import Optional, List
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

@dataclass
class Config:
    """Bot configuration settings."""
    # Discord settings
    discord_token: str
    database_url: str
    redis_url: str
    test_guild_id: Optional[int] = None
    command_prefix: str = "!"

    # Redis settings
    redis_password: Optional[str] = None
    redis_cache_ttl: int = 3600  # Cache TTL in seconds (1 hour default)
    
    # API settings
    xivapi_key: Optional[str] = None
    
    # Logging settings
    logging_level: int = logging.INFO
    log_to_file: bool = False
    log_file_path: Optional[str] = None

def load_config() -> Config:
    """Load configuration from environment variables."""
    # Essential settings
    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        raise ValueError("DISCORD_TOKEN environment variable is required")
    
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/ffxiv_bot")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Optional settings with defaults
    test_guild_id_str = os.getenv("TEST_GUILD_ID")
    test_guild_id = int(test_guild_id_str) if test_guild_id_str else None
    
    command_prefix = os.getenv("COMMAND_PREFIX", "!")
    
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_cache_ttl = int(os.getenv("REDIS_CACHE_TTL", "3600"))
    
    xivapi_key = os.getenv("XIVAPI_KEY")
    
    # Logging settings
    logging_level_name = os.getenv("LOGGING_LEVEL", "INFO")
    logging_level = getattr(logging, logging_level_name.upper(), logging.INFO)
    
    log_to_file = os.getenv("LOG_TO_FILE", "false").lower() in ("true", "1", "yes")
    log_file_path = os.getenv("LOG_FILE_PATH", "logs/bot.log")
    
    return Config(
        discord_token=discord_token,
        test_guild_id=test_guild_id,
        command_prefix=command_prefix,
        database_url=database_url,
        redis_url=redis_url,
        redis_password=redis_password,
        redis_cache_ttl=redis_cache_ttl,
        xivapi_key=xivapi_key,
        logging_level=logging_level,
        log_to_file=log_to_file,
        log_file_path=log_file_path
    )