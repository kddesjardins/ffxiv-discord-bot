"""
Redis caching service for API responses.
"""
import json
import logging
import time
import functools
import asyncio
from typing import Any, Optional, Dict, Union, Callable

import redis.asyncio as redis

from config import load_config

# Logger
logger = logging.getLogger("ffxiv_bot")

# Global Redis client
_redis_client = None
_default_ttl = 3600  # Default TTL in seconds (1 hour)

async def init_redis():
    """Initialize Redis connection."""
    global _redis_client, _default_ttl
    
    config = load_config()
    _default_ttl = config.redis_cache_ttl
    
    try:
        logger.info("Initializing Redis connection...")
        
        # Parse Redis URL
        redis_url = config.redis_url
        
        # Create Redis client
        _redis_client = await redis.from_url(
            redis_url,
            password=config.redis_password,
            decode_responses=True  # Automatically decode to strings
        )
        
        # Test connection
        ping_response = await _redis_client.ping()
        if ping_response:
            logger.info("Redis connection established successfully")
        else:
            logger.warning("Redis ping failed, but connection was established")
            
    except Exception as e:
        logger.error(f"Error connecting to Redis: {e}")
        _redis_client = None
        # Don't raise - bot can function without cache

async def close_redis():
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client:
        logger.info("Closing Redis connection...")
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")

async def cache_get(key: str) -> Optional[Any]:
    """
    Get a value from the cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    if not _redis_client:
        return None
    
    try:
        # Get the value from Redis
        value = await _redis_client.get(f"ffxiv_bot:{key}")
        
        if value:
            # Parse the JSON value
            return json.loads(value)
        
    except Exception as e:
        logger.error(f"Error retrieving from cache: {e}")
    
    return None

async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set a value in the cache.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON encoded)
        ttl: Time-to-live in seconds (or None for default)
        
    Returns:
        True if successful, False otherwise
    """
    if not _redis_client:
        return False
    
    # Use default TTL if not specified
    if ttl is None:
        ttl = _default_ttl
    
    try:
        # JSON encode the value
        json_value = json.dumps(value)
        
        # Set the value in Redis with TTL
        result = await _redis_client.setex(
            f"ffxiv_bot:{key}", 
            ttl,
            json_value
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error setting cache: {e}")
        return False

async def cache_delete(key: str) -> bool:
    """
    Delete a value from the cache.
    
    Args:
        key: Cache key
        
    Returns:
        True if successful, False otherwise
    """
    if not _redis_client:
        return False
    
    try:
        # Delete the key from Redis
        result = await _redis_client.delete(f"ffxiv_bot:{key}")
        return result > 0
        
    except Exception as e:
        logger.error(f"Error deleting from cache: {e}")
        return False

async def cleanup_expired_cache() -> int:
    """
    Clean up expired cache entries.
    This is more of a maintenance function as Redis automatically removes
    expired keys, but it can be useful to explicitly remove entries with patterns.
    
    Returns:
        Number of keys scanned/processed
    """
    if not _redis_client:
        return 0
    
    try:
        # Scan for all bot-related keys
        cursor = 0
        count = 0
        
        while True:
            cursor, keys = await _redis_client.scan(
                cursor=cursor, 
                match="ffxiv_bot:*", 
                count=1000
            )
            
            count += len(keys)
            
            # Stop if we've processed all keys
            if cursor == 0:
                break
        
        logger.info(f"Cache maintenance complete: scanned {count} keys")
        return count
        
    except Exception as e:
        logger.error(f"Error during cache maintenance: {e}")
        return 0

def cached(key_prefix: str, ttl: Optional[int] = None):
    """
    Decorator for caching async function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds (or None for default)
    """
    def decorator(func):
        # Create a dictionary to store the cached results
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Prepare to call the async function
            async def run_async():
                # Generate cache key from function name, args, and kwargs
                cache_key = f"{key_prefix}:{func.__name__}:"
                cache_key += ":".join(str(arg) for arg in args)
                cache_key += ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                
                # Try to get from cache first
                cached_result = await cache_get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Not in cache, call the function
                result = await func(*args, **kwargs)
                
                # Cache the result
                await cache_set(cache_key, result, ttl)
                
                return result
            
            # Run the async function and get the result
            return asyncio.run(run_async())
        
        return wrapper
    return decorator