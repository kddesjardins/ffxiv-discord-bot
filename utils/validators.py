"""
Validation utilities for the FFXIV Discord Bot.

Provides functions to validate various types of input 
used throughout the bot's operations.
"""

import re
import unicodedata
from typing import Optional, Union, Dict, Any

def validate_discord_username(username: str) -> bool:
    """
    Validate a Discord username.
    
    Args:
        username: Discord username to validate
    
    Returns:
        True if username is valid, False otherwise
    """
    # Discord username regex (username#discriminator format)
    # Note: This is a basic validation and might need updates based on Discord's exact rules
    pattern = r'^.{2,32}#\d{4}$'
    return bool(re.match(pattern, username))

def validate_ffxiv_character_name(name: str) -> bool:
    """
    Validate a Final Fantasy XIV character name.
    
    Criteria:
    - Between 2 and 20 characters
    - Allows letters, spaces, hyphens, and apostrophes
    - First character must be a letter
    
    Args:
        name: Character name to validate
    
    Returns:
        True if name is valid, False otherwise
    """
    # Remove accents and normalize
    normalized_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
    
    # Validate name format
    pattern = r'^[A-Za-z][A-Za-z\'\- ]{1,19}$'
    return bool(re.match(pattern, normalized_name))

def validate_ffxiv_server(server: str) -> bool:
    """
    Validate a Final Fantasy XIV server name.
    
    Args:
        server: Server name to validate
    
    Returns:
        True if server name is valid, False otherwise
    """
    # List of known FFXIV data centers and servers
    ffxiv_servers = {
        # North America
        "Aether": ["Adamantoise", "Atomic Heart", "Cactuар", "Coeurl", "Faerie", "Gilgamesh", "Goblin", "Jenova", "Midgardsormr", "Minfillia", "Pandaemonium", "Pixie", "Primal", "Ragnarok", "Siren", "Ultros"],
        
        # Europe
        "Chaos": ["Cerberus", "Louisoix", "Moogle", "Omega", "Phantom", "Ragnarok", "Sagolii", "Spriggan"],
        
        # Japan
        "Elemental": ["Aegis", "Atomos", "Carbuncle", "Garuda", "Gungnir", "Kujata", "Ramuh", "Tonberry", "Typhon"],
        "Gaia": ["Alexander", "Bahamut", "Durandal", "Fenrir", "Ifrit", "Ridill", "Shinryu", "Titan"],
        "Crystal": ["Balmung", "Brynhildr", "Coeurl", "Diabolos", "Excalibur", "Exodus", "Famfrit", "Hyperion", "Lamia", "Leviathan", "Malboro", "Mateus", "Midgardsormr", "Sargatanas", "Siren", "Zalera"],
        "Light": ["Alpha", "Lich", "Moogle", "Odin", "Phoenix", "Raiden", "Shiva", "Zodiark"],
        "Meteor": ["Bismarck", "Ravana", "Sephirot", "Sophia", "Zurvan"]
    }
    
    # Check if server exists in any data center
    for dc_servers in ffxiv_servers.values():
        if server in dc_servers:
            return True
    
    return False

def validate_lodestone_id(lodestone_id: Union[str, int]) -> bool:
    """
    Validate a Lodestone character ID.
    
    Args:
        lodestone_id: Lodestone ID to validate
    
    Returns:
        True if Lodestone ID is valid, False otherwise
    """
    # Convert to string to handle both str and int inputs
    str_id = str(lodestone_id)
    
    # Lodestone ID should be a numeric string of specific length
    return bool(re.match(r'^\d{5,10}$', str_id))

def validate_discord_id(discord_id: Union[str, int]) -> bool:
    """
    Validate a Discord user ID.
    
    Args:
        discord_id: Discord user ID to validate
    
    Returns:
        True if Discord ID is valid, False otherwise
    """
    # Convert to string to handle both str and int inputs
    str_id = str(discord_id)
    
    # Discord ID should be a numeric string
    return bool(re.match(r'^\d{17,19}$', str_id))

def validate_email(email: str) -> bool:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email is valid, False otherwise
    """
    # RFC 5322 Official Standard email validation regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_hex_color(color: str) -> bool:
    """
    Validate a hex color code.
    
    Args:
        color: Hex color code to validate
    
    Returns:
        True if color is a valid hex code, False otherwise
    """
    # Validate both #RRGGBB and RRGGBB formats
    pattern = r'^#?([0-9A-Fa-f]{3}){1,2}$'
    return bool(re.match(pattern, color))

def validate_json_data(data: Any, expected_structure: Optional[Dict[str, type]] = None) -> bool:
    """
    Validate JSON data against an optional expected structure.
    
    Args:
        data: Data to validate
        expected_structure: Optional dictionary specifying expected key types
    
    Returns:
        True if data matches expected structure, False otherwise
    """
    # If no structure is provided, just check if data is a dictionary
    if expected_structure is None:
        return isinstance(data, dict)
    
    # Check if data is a dictionary
    if not isinstance(data, dict):
        return False
    
    # Check each expected key
    for key, expected_type in expected_structure.items():
        # Check if key exists
        if key not in data:
            return False
        
        # Check type of value
        if not isinstance(data[key], expected_type):
            return False
    
    return True