"""
Characters/Groups extension for the FFXIV Discord bot.
"""
from interactions import Extension, Client

class CharactersCog(Extension):
    """
    Cog for character-related commands and functionality.
    """
    def __init__(self, client: Client):
        self.client = client

async def setup(client: Client) -> Extension:
    """
    Setup function for the Characters extension.
    
    Args:
        client: The Discord bot client
    
    Returns:
        An instance of the CharactersCog extension
    """
    return CharactersCog(client)