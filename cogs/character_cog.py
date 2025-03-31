"""
Character management cog for the FFXIV Discord bot.
This file should be placed in the "cogs" directory.
"""
from interactions import Extension, Client

from character_commands import CharacterCommandsCog

async def setup(client: Client) -> Extension:
    """Set up the character management extension."""
    return CharacterCommandsCog(client)