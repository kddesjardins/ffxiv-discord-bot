#!/usr/bin/env python3
"""
FFXIV Character Management Discord Bot
Main entry point for bot initialization and execution.
"""
import os
import sys
import logging
import signal
import asyncio
import importlib.util
from pathlib import Path

from interactions import (
    Client, 
    Intents, 
    listen,
    Task,
    IntervalTrigger
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.logging import setup_logging
from utils.db import init_db_connection, close_db_connection
from services.api_cache import init_redis, close_redis
from config import load_config

# Load configuration
config = load_config()

# Setup logging
logger = setup_logging(config.logging_level)

# Initialize the bot with all intents
bot = Client(
    token=config.discord_token,
    intents=Intents.ALL,
    test_guilds=[config.test_guild_id] if config.test_guild_id else None,
    debug_scope=config.test_guild_id if config.test_guild_id else None
)

# Initialize scheduler
scheduler = AsyncIOScheduler()

@listen()
async def on_ready():
    """Called when the bot is ready to handle commands."""
    logger.info(f"{bot.user.username} is ready! Connected to {len(bot.guilds)} guilds")
    
    try:
        commands = bot.application_commands
        logger.info(f"Registered commands: {[cmd.name for cmd in commands]}")
    except Exception as e:
        logger.error(f"Error fetching commands: {e}")
    
    # Initialize database connection
    await init_db_connection()
    
    # Initialize Redis connection
    await init_redis()
    
    # Start scheduled tasks
    scheduler.start()
    
    # Schedule API cache cleanup
    @Task.create(IntervalTrigger(hours=1))
    async def cleanup_cache():
        """Clean up expired cache entries hourly"""
        from services.api_cache import cleanup_expired_cache
        await cleanup_expired_cache()
    
    # Schedule database checks
    @Task.create(IntervalTrigger(hours=24))
    async def db_maintenance():
        """Perform database maintenance daily"""
        from utils.db import perform_maintenance
        await perform_maintenance()

async def load_single_extension(extension_name: str, is_priority: bool = False):
    """Load a single extension by name."""
    try:
        # Extract just the module name from the full path
        module_name = extension_name.split('.')[-1]
        
        # Build the path to the module file
        module_path = Path(__file__).parent / f"{extension_name.replace('.', '/')}.py"
        
        # Get the module spec
        spec = importlib.util.spec_from_file_location(
            extension_name,  # Use full extension name
            str(module_path)
        )
        
        if not spec or not spec.loader:
            raise ImportError(f"Could not find module spec for {extension_name}")

        # Create the module and set its name
        module = importlib.util.module_from_spec(spec)
        module.__name__ = extension_name
        sys.modules[extension_name] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Call setup function and register extension
        extension = await module.setup(bot)
        if not extension:
            raise ValueError(f"Setup function for {extension_name} returned None")
            
        msg = "priority extension" if is_priority else "extension"
        logger.info(f"Loaded {msg}: {extension_name}")
        
    except Exception as e:
        logger.error(f"Failed to load {'priority ' if is_priority else ''}extension {extension_name}: {e}")
        logger.error("Stack trace:", exc_info=True)
        if is_priority:
            raise e
        
async def load_extensions():
    """Load all extensions with priority ordering."""
    # Priority extensions that must be loaded first
    priority_extensions = [
        "cogs.managers",    # Load managers first (permissions)
        "cogs.characters",  # Character management
        "cogs.groups",      # Group management
    ]

    # Load priority extensions first
    for extension in priority_extensions:
        await load_single_extension(extension, is_priority=True)

    # Load remaining extensions
    cogs_dir = Path(__file__).parent / 'cogs'
    excluded_files = ['__init__.py', '__pycache__']  # Files to exclude
    
    for filepath in cogs_dir.glob('*.py'):
        filename = filepath.name
        if filename not in excluded_files:
            extension_name = f'cogs.{filename[:-3]}'
            if extension_name not in priority_extensions:
                await load_single_extension(extension_name)

async def shutdown(signal, loop):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    
    try:
        # Stop the scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
        
        # Close Redis connection
        await close_redis()
        
        # Close database connection
        await close_db_connection()
        
        # Stop the bot
        if hasattr(bot, '_ready') and bot._ready.is_set():
            await bot.stop()
        
        # Cancel all tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop the event loop
        loop.stop()
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

async def main():
    """Main entry point for the bot."""
    try:
        logger.info("Starting FFXIV Character Management Bot")
        await load_extensions()
        await bot.astart()
    except asyncio.CancelledError:
        logger.info("Bot startup cancelled")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    if not config.discord_token:
        logger.error("DISCORD_TOKEN environment variable not set")
        sys.exit(1)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Handle signals
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop))
        )
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("Successfully shutdown the bot.")