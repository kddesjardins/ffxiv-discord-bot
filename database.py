"""
Database utilities for the FFXIV Discord bot.
Simple SQLite implementation for character storage.
"""
import os
import sqlite3
import logging
from typing import Optional, List, Dict, Any

# Set up logger
logger = logging.getLogger("ffxiv_bot")

# Database file path
DB_PATH = "ffxiv_bot.db"

def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
    return conn

def initialize_db():
    """Create necessary tables if they don't exist."""
    logger.info("Initializing database...")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create characters table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        server TEXT NOT NULL,
        lodestone_id TEXT,
        discord_user_id TEXT NOT NULL,
        is_primary BOOLEAN DEFAULT 0,
        verified BOOLEAN DEFAULT 0,
        job_level INTEGER,
        active_job TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create MSQ progress table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS msq_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        expansion TEXT NOT NULL,
        progress INTEGER NOT NULL,
        completed BOOLEAN DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
    )
    ''')
    
    # Create indices for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_character_discord_id ON characters (discord_user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_character_name_server ON characters (name, server)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_character_lodestone ON characters (lodestone_id)')
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialization complete")

def add_character(discord_user_id: str, name: str, server: str, 
                  lodestone_id: Optional[str] = None, is_primary: bool = False) -> int:
    """
    Add a new character to the database.
    
    Args:
        discord_user_id: Discord user ID of the character owner
        name: Character name
        server: Character server
        lodestone_id: Optional Lodestone ID
        is_primary: Whether this is the user's primary character
        
    Returns:
        The ID of the newly created character
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # If this is set as primary, un-set any existing primary characters for this user
        if is_primary:
            cursor.execute(
                "UPDATE characters SET is_primary = 0 WHERE discord_user_id = ?",
                (discord_user_id,)
            )
        
        # Insert the new character
        cursor.execute(
            "INSERT INTO characters (discord_user_id, name, server, lodestone_id, is_primary) VALUES (?, ?, ?, ?, ?)",
            (discord_user_id, name, server, lodestone_id, is_primary)
        )
        
        char_id = cursor.lastrowid
        conn.commit()
        return char_id
    except sqlite3.Error as e:
        logger.error(f"Database error adding character: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_character(character_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a character by ID.
    
    Args:
        character_id: Character ID
        
    Returns:
        Character data as a dictionary, or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (character_id,)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def get_character_by_name_server(name: str, server: str) -> Optional[Dict[str, Any]]:
    """
    Get a character by name and server.
    
    Args:
        name: Character name
        server: Character server
        
    Returns:
        Character data as a dictionary, or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM characters WHERE name LIKE ? AND server LIKE ?",
        (name, server)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def get_user_characters(discord_user_id: str) -> List[Dict[str, Any]]:
    """
    Get all characters for a Discord user.
    
    Args:
        discord_user_id: Discord user ID
        
    Returns:
        List of character dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM characters WHERE discord_user_id = ? ORDER BY is_primary DESC, name ASC",
        (discord_user_id,)
    )
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_primary_character(discord_user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user's primary character.
    
    Args:
        discord_user_id: Discord user ID
        
    Returns:
        Primary character data as a dictionary, or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM characters WHERE discord_user_id = ? AND is_primary = 1",
        (discord_user_id,)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def set_primary_character(character_id: int, discord_user_id: str) -> bool:
    """
    Set a character as the primary character for a user.
    
    Args:
        character_id: Character ID to set as primary
        discord_user_id: Discord user ID (for verification)
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify the character belongs to the user
        cursor.execute(
            "SELECT id FROM characters WHERE id = ? AND discord_user_id = ?",
            (character_id, discord_user_id)
        )
        if not cursor.fetchone():
            logger.warning(f"User {discord_user_id} tried to set primary character {character_id} they don't own")
            return False
        
        # Clear existing primary
        cursor.execute(
            "UPDATE characters SET is_primary = 0 WHERE discord_user_id = ?",
            (discord_user_id,)
        )
        
        # Set new primary
        cursor.execute(
            "UPDATE characters SET is_primary = 1 WHERE id = ?",
            (character_id,)
        )
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error setting primary character: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def mark_character_verified(character_id: int, lodestone_id: str = None) -> bool:
    """
    Mark a character as verified.
    
    Args:
        character_id: Character ID
        lodestone_id: Optional Lodestone ID to update
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if lodestone_id:
            cursor.execute(
                "UPDATE characters SET verified = 1, lodestone_id = ? WHERE id = ?",
                (lodestone_id, character_id)
            )
        else:
            cursor.execute(
                "UPDATE characters SET verified = 1 WHERE id = ?",
                (character_id,)
            )
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error marking character as verified: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_character_job(character_id: int, job: str, level: int) -> bool:
    """
    Update a character's active job and level.
    
    Args:
        character_id: Character ID
        job: Job name
        level: Job level
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE characters SET active_job = ?, job_level = ? WHERE id = ?",
            (job, level, character_id)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error updating character job: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def remove_character(character_id: int, discord_user_id: str) -> bool:
    """
    Remove a character from the database.
    
    Args:
        character_id: Character ID to remove
        discord_user_id: Discord user ID (for verification)
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify the character belongs to the user
        cursor.execute(
            "SELECT id FROM characters WHERE id = ? AND discord_user_id = ?",
            (character_id, discord_user_id)
        )
        if not cursor.fetchone():
            logger.warning(f"User {discord_user_id} tried to remove character {character_id} they don't own")
            return False
        
        # Delete the character (cascade will remove related records)
        cursor.execute(
            "DELETE FROM characters WHERE id = ?",
            (character_id,)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error removing character: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()