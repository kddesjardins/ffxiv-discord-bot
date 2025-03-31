#!/usr/bin/env python3
"""
FFXIV Character Management Discord Bot
Main entry point for bot initialization and execution.
"""
import os
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from interactions import (
    Client, 
    Intents, 
    listen,
    slash_command,
    SlashContext,
    Embed
)

# Load environment variables from .env file if present
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ffxiv_bot")

# Initialize the bot with necessary intents
bot = Client(
    token=os.getenv("DISCORD_TOKEN"),
    intents=Intents.DEFAULT,
    test_guilds=[int(os.getenv("TEST_GUILD_ID"))] if os.getenv("TEST_GUILD_ID") else None
)

@listen()
async def on_ready():
    """Called when the bot is ready to handle commands."""
    logger.info(f"{bot.user.username} is ready! Connected to {len(bot.guilds)} guilds")
    
    try:
        commands = bot.application_commands
        logger.info(f"Registered commands: {[cmd.name for cmd in commands]}")
    except Exception as e:
        logger.error(f"Error fetching commands: {e}")

@slash_command(
    name="ping",
    description="Check if the bot is responsive",
)
async def ping(ctx: SlashContext):
    """Simple ping command to check if the bot is responsive."""
    await ctx.send("Pong! Bot is up and running!")

async def load_extensions():
    """Load all extensions from the cogs directory."""
    # Create the cogs directory if it doesn't exist
    cogs_dir = Path("cogs")
    cogs_dir.mkdir(exist_ok=True)
    
    # First, check if character_lookup.py exists in the current directory
    lookup_file = Path("character_lookup.py")
    if lookup_file.exists():
        # Create a simple cog file in the cogs directory
        with open(cogs_dir / "lookup_cog.py", "w") as f:
            f.write('''"""
Character lookup cog for the FFXIV Discord bot.
"""
from interactions import Extension, Client
from character_lookup import CharacterLookupCog

async def setup(client: Client) -> Extension:
    """Set up the character lookup extension."""
    return CharacterLookupCog(client)
''')
    
    # Then load all extensions from the cogs directory
    for filepath in cogs_dir.glob("*.py"):
        filename = filepath.name
        
        # Skip files that shouldn't be loaded
        if filename.startswith("_") or filename == "__init__.py":
            continue
        
        # Extract the extension name 
        extension_name = f"cogs.{filename[:-3]}"
        
        try:
            # Load the extension
            await bot.load_extension(extension_name)
            logger.info(f"Loaded extension: {extension_name}")
        except Exception as e:
            logger.error(f"Failed to load extension {extension_name}: {e}")

if __name__ == "__main__":
    if not os.getenv("DISCORD_TOKEN"):
        logger.error("DISCORD_TOKEN environment variable not set")
        exit(1)
    
    logger.info("Starting FFXIV Character Management Bot")
    
    # Create .env file with empty XIVAPI_KEY if it doesn't exist
    if not os.path.exists(".env"):
        with open(".env", "a") as f:
            f.write("\nXIVAPI_KEY=")
        logger.info("Created .env file with empty XIVAPI_KEY")
    elif "XIVAPI_KEY" not in os.environ:
        with open(".env", "a") as f:
            f.write("\nXIVAPI_KEY=")
        logger.info("Added empty XIVAPI_KEY to .env file")
    
    # Load extensions
    asyncio.run(load_extensions())
    
    bot.start()