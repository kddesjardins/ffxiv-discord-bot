"""
Character management commands for the FFXIV Discord bot.
"""
import logging
from typing import Optional, Dict, Any

from interactions import (
    Extension,
    Client,
    SlashContext,
    slash_command,
    slash_option,
    OptionType,
    Embed,
    Button,
    ButtonStyle,
    ActionRow,
    ComponentContext,
    component_callback,
    Modal,
    TextStyles,
)
from interactions.api.events import ModalContext

from services.xivapi import XIVAPI
from utils.db import get_db_session
from utils.logging import get_logger

# Logger
logger = get_logger()

class CharactersCog(Extension):
    """
    Character management extension for the FFXIV Discord bot.
    Provides commands for registering, updating, and managing FFXIV characters.
    """
    
    def __init__(self, client: Client):
        """
        Initialize the Characters extension.
        
        Args:
            client: The Discord bot client
        """
        self.client = client
        self.xivapi = XIVAPI()
    
    @slash_command(
        name="character",
        description="Character management commands",
    )
    async def character_command(self, ctx: SlashContext):
        """
        Base command group for character management.
        """
        # This is a command group and doesn't need its own implementation
        pass
    
    @character_command.subcommand(
        sub_cmd_name="register",
        sub_cmd_description="Register a new FFXIV character",
    )
    @slash_option(
        name="name",
        description="Character name",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="server",
        description="Character's server",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="primary",
        description="Set as primary character",
        required=False,
        opt_type=OptionType.BOOLEAN
    )
    async def character_register(
        self, 
        ctx: SlashContext, 
        name: str, 
        server: str, 
        primary: bool = False
    ):
        """
        Register a new character for the user.
        
        Args:
            ctx: The interaction context
            name: Character name
            server: Character's server
            primary: Whether to set as primary character
        """
        # Defer response while processing
        await ctx.defer()
        
        try:
            # Search for character on XIVAPI
            search_results = await self.xivapi.search_character(name, server)
            
            # Check if character exists
            if not search_results or 'Results' not in search_results:
                return await ctx.send(f"No character found named {name} on {server}.")
            
            # Get the first matching character
            character_data = search_results['Results'][0]
            
            async with get_db_session() as session:
                # Check if character is already registered
                query = """
                    SELECT id FROM characters 
                    WHERE lodestone_id = $1
                """
                result = await session.execute(query, character_data['ID'])
                existing_char = await result.fetchone()
                
                if existing_char:
                    return await ctx.send(f"Character {name} is already registered.")
                
                # If setting as primary, unset previous primary
                if primary:
                    query = """
                        UPDATE characters 
                        SET is_primary = FALSE 
                        WHERE discord_user_id = $1
                    """
                    await session.execute(query, str(ctx.author.id))
                
                # Insert new character
                query = """
                    INSERT INTO characters (
                        name, server, lodestone_id, discord_user_id, 
                        is_primary, avatar_url, portrait_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """
                result = await session.execute(
                    query,
                    name,
                    server,
                    character_data['ID'],
                    str(ctx.author.id),
                    primary,
                    character_data.get('Avatar', ''),
                    character_data.get('Portrait', '')
                )
                
                # Create embed response
                embed = Embed(
                    title="Character Registered",
                    description=f"Successfully registered **{name}** from {server}",
                    color=0x2ecc71
                )
                
                # Add character details
                embed.add_field(name="Lodestone ID", value=character_data['ID'], inline=True)
                embed.add_field(name="Primary Character", value="Yes" if primary else "No", inline=True)
                
                # Add buttons for next steps
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="Verify Ownership",
                        custom_id=f"verify_character:{character_data['ID']}"
                    ),
                    Button(
                        style=ButtonStyle.SECONDARY,
                        label="View Character",
                        custom_id=f"view_character:{character_data['ID']}"
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error registering character: {e}")
            return await ctx.send("An error occurred while registering the character. Please try again later.")
    
    @character_command.subcommand(
        sub_cmd_name="list",
        sub_cmd_description="List your registered characters",
    )
    async def character_list(self, ctx: SlashContext):
        """
        List characters registered by the user.
        
        Args:
            ctx: The interaction context
        """
        # Defer response while processing
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Fetch all characters for this user
                query = """
                    SELECT id, name, server, lodestone_id, is_primary, 
                           active_class_job, msq_progress
                    FROM characters
                    WHERE discord_user_id = $1
                    ORDER BY is_primary DESC, name ASC
                """
                result = await session.execute(query, str(ctx.author.id))
                characters = await result.fetchall()
                
                if not characters:
                    return await ctx.send("You have no registered characters. Use `/character register` to add one.")
                
                # Create embed response
                embed = Embed(
                    title="Your FFXIV Characters",
                    description=f"Total characters: {len(characters)}",
                    color=0x3498db
                )
                
                # Add each character as a field
                for char in characters:
                    # Format character details
                    primary_marker = "★ " if char['is_primary'] else ""
                    job = char['active_class_job'] or "No job set"
                    msq_progress = char['msq_progress'] or "No progress recorded"
                    
                    # Create field value
                    value = (
                        f"**Server:** {char['server']}\n"
                        f"**Job:** {job}\n"
                        f"**MSQ:** {msq_progress}\n"
                        f"**Lodestone ID:** {char['lodestone_id']}"
                    )
                    
                    embed.add_field(
                        name=f"{primary_marker}{char['name']}",
                        value=value,
                        inline=False
                    )
                
                # Add buttons for actions
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="Register New Character",
                        custom_id="register_new_character"
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            return await ctx.send("An error occurred while retrieving your characters. Please try again later.")

async def setup(client: Client) -> Extension:
    """
    Setup function for the Characters extension.
    
    Args:
        client: The Discord bot client
    
    Returns:
        An instance of the CharactersCog extension
    """
    return CharactersCog(client)