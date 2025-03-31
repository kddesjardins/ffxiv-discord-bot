#!/usr/bin/env python3
"""
FFXIV Character Management Discord Bot - Simplified Version
Main entry point for bot initialization and execution.
"""
import os
import logging
from dotenv import load_dotenv

from interactions import (
    Client, 
    Intents, 
    listen,
    slash_command,
    slash_option,
    SlashContext,
    OptionType,
    Embed,
    ButtonStyle,
    Button,
    ActionRow
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

@slash_command(
    name="character",
    description="Character management commands",
)
async def character_command(ctx: SlashContext):
    """Character management command group."""
    # This is a command group and doesn't need its own implementation
    pass

@character_command.subcommand(
    sub_cmd_name="register",
    sub_cmd_description="Register a new character",
)
@slash_option(
    name="name",
    description="Character name",
    required=True,
    opt_type=OptionType.STRING
)
@slash_option(
    name="server",
    description="Character server",
    required=True,
    opt_type=OptionType.STRING
)
async def character_register(ctx: SlashContext, name: str, server: str):
    """Register a new character."""
    # Defer response while we process
    await ctx.defer()
    
    try:
        # In a full implementation, you would save this to a database
        # For now, just acknowledge the registration
        
        embed = Embed(
            title="Character Registered",
            description=f"Successfully registered {name} on {server}",
            color=0x3498db
        )
        
        embed.add_field(name="Character Name", value=name, inline=True)
        embed.add_field(name="Server", value=server, inline=True)
        embed.add_field(name="Owner", value=ctx.author.mention, inline=True)
        
        # Add a button for future verification step
        components = ActionRow(
            Button(
                style=ButtonStyle.PRIMARY,
                label="Verify Character",
                custom_id=f"verify_character:{name}:{server}"
            )
        )
        
        await ctx.send(embed=embed, components=components)
        
    except Exception as e:
        logger.error(f"Error registering character: {e}")
        await ctx.send("An error occurred while registering your character. Please try again later.")

@character_command.subcommand(
    sub_cmd_name="list",
    sub_cmd_description="List your registered characters",
)
async def character_list(ctx: SlashContext):
    """List registered characters."""
    # Defer response while we process
    await ctx.defer()
    
    try:
        # In a full implementation, you would fetch this from a database
        # For now, just show a placeholder
        
        embed = Embed(
            title="Your FFXIV Characters",
            description="In the full implementation, this would list your registered characters from the database.",
            color=0x3498db
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        await ctx.send("An error occurred while listing your characters. Please try again later.")

@slash_command(
    name="msq",
    description="MSQ progression commands",
)
async def msq_command(ctx: SlashContext):
    """MSQ progression command group."""
    # This is a command group and doesn't need its own implementation
    pass

@msq_command.subcommand(
    sub_cmd_name="update",
    sub_cmd_description="Update MSQ progression for your character",
)
@slash_option(
    name="expansion",
    description="Current expansion",
    required=True,
    opt_type=OptionType.STRING,
    choices=[
        {"name": "A Realm Reborn", "value": "arr"},
        {"name": "Heavensward", "value": "hw"},
        {"name": "Stormblood", "value": "sb"},
        {"name": "Shadowbringers", "value": "shb"},
        {"name": "Endwalker", "value": "ew"},
        {"name": "Dawntrail", "value": "dt"}
    ]
)
@slash_option(
    name="progress",
    description="Progress within expansion",
    required=True,
    opt_type=OptionType.STRING,
    choices=[
        {"name": "Just Started", "value": "started"},
        {"name": "About 25% Complete", "value": "25pct"},
        {"name": "About 50% Complete", "value": "50pct"},
        {"name": "About 75% Complete", "value": "75pct"},
        {"name": "Main Story Complete", "value": "complete"},
        {"name": "Post-MSQ Patches Complete", "value": "patches"}
    ]
)
async def msq_update(ctx: SlashContext, expansion: str, progress: str):
    """Update MSQ progression for a character."""
    # Defer response while we process
    await ctx.defer()
    
    try:
        # Map expansion shorthand to full name
        expansion_map = {
            "arr": "A Realm Reborn",
            "hw": "Heavensward",
            "sb": "Stormblood",
            "shb": "Shadowbringers",
            "ew": "Endwalker",
            "dt": "Dawntrail"
        }
        
        # Map progress to display text
        progress_map = {
            "started": "Just Started",
            "25pct": "About 25% Complete",
            "50pct": "About 50% Complete",
            "75pct": "About 75% Complete",
            "complete": "Main Story Complete",
            "patches": "Post-MSQ Patches Complete"
        }
        
        expansion_name = expansion_map.get(expansion, expansion)
        progress_name = progress_map.get(progress, progress)
        
        # In a full implementation, you would save this to a database
        # For now, just acknowledge the update
        
        embed = Embed(
            title="MSQ Progress Updated",
            description=f"Successfully updated MSQ progress",
            color=0x3498db
        )
        
        embed.add_field(name="Expansion", value=expansion_name, inline=True)
        embed.add_field(name="Progress", value=progress_name, inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error updating MSQ progress: {e}")
        await ctx.send("An error occurred while updating MSQ progress. Please try again later.")

if __name__ == "__main__":
    if not os.getenv("DISCORD_TOKEN"):
        logger.error("DISCORD_TOKEN environment variable not set")
        exit(1)
    
    logger.info("Starting FFXIV Character Management Bot")
    bot.start()