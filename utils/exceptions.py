"""
General utility functions for the FFXIV Discord bot.
"""
import re
import unicodedata
from typing import Optional, Union

def sanitize_input(input_string: str, max_length: int = 100) -> str:
    """
    Sanitize user input by:
    - Removing non-printable characters
    - Trimming to max length
    - Normalizing unicode characters
    
    Args:
        input_string: The input string to sanitize
        max_length: Maximum allowed length of the string
    
    Returns:
        Sanitized string
    """
    if not input_string:
        return ""
    
    # Normalize unicode characters
    normalized = unicodedata.normalize('NFKD', input_string)
    
    # Remove non-printable characters
    cleaned = re.sub(r'[^\x20-\x7E]', '', normalized)
    
    # Trim to max length
    return cleaned[:max_length].strip()

def format_discord_mention(user_id: Union[int, str]) -> str:
    """
    Format a user ID into a Discord mention.
    
    Args:
        user_id: Discord user ID
    
    Returns:
        Formatted mention string
    """
    return f"<@{user_id}>"

def parse_discord_mention(mention: str) -> Optional[str]:
    """
    Extract user ID from a Discord mention.
    
    Args:
        mention: Discord mention string
    
    Returns:
        User ID or None if invalid mention
    """
    # Regex to match Discord mentions
    match = re.match(r'<@!?(\d+)>', mention)
    return match.group(1) if match else None

def truncate_text(text: str, max_length: int = 1024, suffix: str = '...') -> str:
    """
    Truncate text to a specified maximum length.
    
    Args:
        text: Input text to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add when text is truncated
    
    Returns:
        Truncated text
    """
    if not text:
        return text
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from a given text.
    
    Args:
        text: Input text to convert to a slug
    
    Returns:
        Lowercased, hyphenated slug
    """
    # Normalize unicode characters
    normalized = unicodedata.normalize('NFKD', text)
    
    # Remove non-alphanumeric characters and replace with hyphens
    slug = re.sub(r'[^\w\s-]', '', normalized.lower())
    
    # Replace whitespace with hyphens
    slug = re.sub(r'[-\s]+', '-', slug).strip('-_')
    
    return slug

class LRUCache:
    """
    Simple Least Recently Used (LRU) Cache implementation.
    
    Attributes:
        capacity: Maximum number of items to store in cache
    """
    def __init__(self, capacity: int = 128):
        """
        Initialize the LRU cache.
        
        Args:
            capacity: Maximum number of items to store
        """
        self.capacity = capacity
        self._cache = {}
        self._key_order = []
    
    def get(self, key):
        """
        Retrieve an item from the cache.
        
        Args:
            key: Cache key to retrieve
        
        Returns:
            Cached value or None if not found
        """
        if key not in self._cache:
            return None
        
        # Move the key to the end to mark as most recently used
        self._key_order.remove(key)
        self._key_order.append(key)
        
        return self._cache[key]
    
    def put(self, key, value):
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to store
        """
        # If key already exists, remove it from order
        if key in self._cache:
            self._key_order.remove(key)
        
        # Add to cache
        self._cache[key] = value
        self._key_order.append(key)
        
        # Evict least recently used items if over capacity
        while len(self._key_order) > self.capacity:
            oldest_key = self._key_order.pop(0)
            del self._cache[oldest_key]
    
    def clear(self):
        """Clear the entire cache."""
        self._cache.clear()
        self._key_order.clear()