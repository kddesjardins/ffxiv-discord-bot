"""
Mount and minion farming commands for the FFXIV Discord bot.
"""
import logging
from typing import Dict, Any, List, Optional

from interactions import (
    Extension,
    Client,
    SlashContext,
    slash_command,
    slash_option,
    SlashCommandOption,
    OptionType,
    Embed,
    EmbedField,
    EmbedFooter,
    ButtonStyle,
    Button,
    ActionRow,
    ComponentContext,
    component_callback,
    listen
)
import asyncpg

from services.xivapi import XIVAPI
from services.ffxivcollect import FFXIVCollectAPI
from services.recommendation import RecommendationEngine
from utils.db import get_db_session
from utils.logging import get_logger

# Logger
logger = get_logger()

class FarmingCog(Extension):
    """Mount and minion farming commands."""
    
    def __init__(self, client: Client):
        self.client = client
        self.xivapi = XIVAPI()
        self.ffxivcollect = FFXIVCollectAPI()
        self.recommendation_engine = RecommendationEngine(self.ffxivcollect, self.xivapi)
    
    @slash_command(
        name="farm",
        description="Mount and minion farming commands",
    )
    async def farm_command(self, ctx: SlashContext):
        """Mount and minion farming command group."""
        # This is a command group and doesn't need its own implementation
        pass
    
    @farm_command.subcommand(
        sub_cmd_name="missing",
        sub_cmd_description="Show missing mounts or minions for a character",
    )
    @slash_option(
        name="type",
        description="What to look for",
        required=True,
        opt_type=OptionType.STRING,
        choices=[
            {"name": "Mounts", "value": "mounts"},
            {"name": "Minions", "value": "minions"}
        ]
    )
    @slash_option(
        name="character",
        description="Character to check (defaults to your primary character)",
        required=False,
        opt_type=OptionType.STRING
    )
    async def farm_missing(self, ctx: SlashContext, type: str, character: str = None):
        """Show missing mounts or minions for a character."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Find the character (primary if not specified)
                if character:
                    # Try to find by name first
                    query = """
                        SELECT id, name, server, lodestone_id, discord_user_id
                        FROM characters
                        WHERE name ILIKE $1 AND discord_user_id = $2
                        LIMIT 1
                    """
                    result = await session.execute(query, character, str(ctx.author.id))
                    char = await result.fetchone()
                    
                    if not char:
                        # Try by Lodestone ID
                        query = """
                            SELECT id, name, server, lodestone_id, discord_user_id
                            FROM characters
                            WHERE lodestone_id = $1
                            LIMIT 1
                        """
                        result = await session.execute(query, character)
                        char = await result.fetchone()
                        
                        if not char:
                            return await ctx.send(f"Character '{character}' not found. Please register it first with `/character register`.")
                else:
                    # Get primary character
                    query = """
                        SELECT id, name, server, lodestone_id, discord_user_id
                        FROM characters
                        WHERE discord_user_id = $1 AND is_primary = TRUE
                        LIMIT 1
                    """
                    result = await session.execute(query, str(ctx.author.id))
                    char = await result.fetchone()
                    
                    if not char:
                        return await ctx.send("No primary character found. Please register a character with `/character register` or specify a character name.")
                
                # Check if character belongs to the user or is publicly visible
                if char['discord_user_id'] != str(ctx.author.id):
                    # For simplicity, we'll allow this but note that the character belongs to someone else
                    # In a real implementation, you'd check permissions more carefully
                    character_owner = f"<@{char['discord_user_id']}>"
                else:
                    character_owner = None
                
                # Get progress message
                progress_embed = Embed(
                    title=f"Checking Missing {type.capitalize()}",
                    description=f"Looking up collection data for {char['name']} ({char['server']})...",
                    color=0x3498db
                )
                progress_message = await ctx.send(embed=progress_embed)
                
                # Get missing items
                lodestone_id = char['lodestone_id']
                
                if type == "mounts":
                    missing_items = await self.ffxivcollect.get_missing_mounts(lodestone_id)
                else:  # minions
                    missing_items = await self.ffxivcollect.get_missing_minions(lodestone_id)
                
                # Filter to only farmable items
                farmable_items = []
                for item in missing_items:
                    # Check if item has a farmable source
                    sources = item.get('sources', [])
                    has_farmable_source = False
                    
                    for source in sources:
                        source_type = source.get('type', '')
                        if source_type in ['Dungeon', 'Trial', 'Raid', 'Alliance Raid', 'FATE']:
                            has_farmable_source = True
                            break
                    
                    if has_farmable_source:
                        farmable_items.append(item)
                
                # Create embed response
                embed = Embed(
                    title=f"Missing Farmable {type.capitalize()} for {char['name']}",
                    description=(
                        f"Character: **{char['name']}** ({char['server']})\n"
                        f"Total missing: {len(missing_items)}\n"
                        f"Farmable missing: {len(farmable_items)}"
                    ),
                    color=0x3498db
                )
                
                if character_owner:
                    embed.add_field(name="Character Owner", value=character_owner, inline=True)
                
                # For larger amounts, just show the top 10
                items_to_show = farmable_items[:10]
                
                if items_to_show:
                    # Create fields for each item
                    for item in items_to_show:
                        # Format source information
                        sources_text = ""
                        for source in item.get('sources', []):
                            source_type = source.get('type', '')
                            if source_type in ['Dungeon', 'Trial', 'Raid', 'Alliance Raid', 'FATE']:
                                # Handle related duty if available
                                if 'related_duty' in source and source['related_duty']:
                                    duty = source['related_duty']
                                    duty_name = duty.get('name', '')
                                    duty_level = duty.get('level', 0)
                                    
                                    sources_text += f"• {source_type}: {duty_name} (Level {duty_level})\n"
                                else:
                                    text = source.get('text', '')
                                    sources_text += f"• {source_type}: {text}\n"
                        
                        embed.add_field(
                            name=item['name'],
                            value=sources_text[:1024] if sources_text else "No source information available",
                            inline=False
                        )
                else:
                    embed.add_field(name="No Farmable Items Found", value="All missing items are from non-farmable sources.", inline=False)
                
                # Add footer with pagination info if needed
                if len(farmable_items) > 10:
                    embed.set_footer(text=f"Showing 10/{len(farmable_items)} farmable items. Use the 'View More' button to see more.")
                
                # Add buttons for actions
                components = []
                
                if len(farmable_items) > 10:
                    # Add pagination buttons
                    components.append(
                        ActionRow(
                            Button(
                                style=ButtonStyle.PRIMARY,
                                label="View More",
                                custom_id=f"view_more_missing:{type}:{lodestone_id}:10"
                            )
                        )
                    )
                
                # Add recommendation button
                components.append(
                    ActionRow(
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Get Recommendations",
                            custom_id=f"recommend_for_character:{type}:{lodestone_id}"
                        )
                    )
                )
                
                # Update the message
                await progress_message.edit(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error getting missing items: {e}")
            return await ctx.send(f"An error occurred while retrieving missing items. Please try again later.")
    
    @component_callback("view_more_missing")
    async def view_more_missing_callback(self, ctx: ComponentContext):
        """Handle viewing more missing items."""
        # Get parameters from button custom ID
        parts = ctx.custom_id.split(":")
        type_name = parts[1]  # mounts or minions
        lodestone_id = parts[2]
        offset = int(parts[3])
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the character
                query = """
                    SELECT id, name, server, lodestone_id, discord_user_id
                    FROM characters
                    WHERE lodestone_id = $1
                    LIMIT 1
                """
                result = await session.execute(query, lodestone_id)
                char = await result.fetchone()
                
                if not char:
                    return await ctx.edit_origin(
                        content="Character not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Check if character belongs to the user or is publicly visible
                if char['discord_user_id'] != str(ctx.author.id):
                    character_owner = f"<@{char['discord_user_id']}>"
                else:
                    character_owner = None
                
                # Get missing items
                if type_name == "mounts":
                    missing_items = await self.ffxivcollect.get_missing_mounts(lodestone_id)
                else:  # minions
                    missing_items = await self.ffxivcollect.get_missing_minions(lodestone_id)
                
                # Filter to only farmable items
                farmable_items = []
                for item in missing_items:
                    # Check if item has a farmable source
                    sources = item.get('sources', [])
                    has_farmable_source = False
                    
                    for source in sources:
                        source_type = source.get('type', '')
                        if source_type in ['Dungeon', 'Trial', 'Raid', 'Alliance Raid', 'FATE']:
                            has_farmable_source = True
                            break
                    
                    if has_farmable_source:
                        farmable_items.append(item)
                
                # Calculate pagination
                items_per_page = 10
                start_idx = offset
                end_idx = min(start_idx + items_per_page, len(farmable_items))
                items_to_show = farmable_items[start_idx:end_idx]
                
                # Create embed response
                embed = Embed(
                    title=f"Missing Farmable {type_name.capitalize()} for {char['name']}",
                    description=(
                        f"Character: **{char['name']}** ({char['server']})\n"
                        f"Total missing: {len(missing_items)}\n"
                        f"Farmable missing: {len(farmable_items)}"
                    ),
                    color=0x3498db
                )
                
                if character_owner:
                    embed.add_field(name="Character Owner", value=character_owner, inline=True)
                
                if items_to_show:
                    # Create fields for each item
                    for item in items_to_show:
                        # Format source information
                        sources_text = ""
                        for source in item.get('sources', []):
                            source_type = source.get('type', '')
                            if source_type in ['Dungeon', 'Trial', 'Raid', 'Alliance Raid', 'FATE']:
                                # Handle related duty if available
                                if 'related_duty' in source and source['related_duty']:
                                    duty = source['related_duty']
                                    duty_name = duty.get('name', '')
                                    duty_level = duty.get('level', 0)
                                    
                                    sources_text += f"• {source_type}: {duty_name} (Level {duty_level})\n"
                                else:
                                    text = source.get('text', '')
                                    sources_text += f"• {source_type}: {text}\n"
                        
                        embed.add_field(
                            name=item['name'],
                            value=sources_text[:1024] if sources_text else "No source information available",
                            inline=False
                        )
                else:
                    embed.add_field(name="No More Items", value="You've reached the end of the list.", inline=False)
                
                # Add footer with pagination info
                embed.set_footer(text=f"Showing {start_idx+1}-{end_idx}/{len(farmable_items)} farmable items")
                
                # Create pagination buttons
                components = []
                pagination_buttons = []
                
                if start_idx > 0:
                    # Add previous page button
                    pagination_buttons.append(
                        Button(
                            style=ButtonStyle.SECONDARY,
                            label="Previous",
                            custom_id=f"view_more_missing:{type_name}:{lodestone_id}:{max(0, start_idx - items_per_page)}"
                        )
                    )
                
                if end_idx < len(farmable_items):
                    # Add next page button
                    pagination_buttons.append(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="Next",
                            custom_id=f"view_more_missing:{type_name}:{lodestone_id}:{end_idx}"
                        )
                    )
                
                if pagination_buttons:
                    components.append(ActionRow(*pagination_buttons))
                
                # Add recommendation button
                components.append(
                    ActionRow(
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Get Recommendations",
                            custom_id=f"recommend_for_character:{type_name}:{lodestone_id}"
                        )
                    )
                )
                
                # Update the message
                await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error viewing more missing items: {e}")
            return await ctx.edit_origin(
                content="An error occurred while retrieving more items. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @component_callback("recommend_for_character")
    async def recommend_for_character_callback(self, ctx: ComponentContext):
        """Handle getting recommendations for a character."""
        # Get parameters from button custom ID
        parts = ctx.custom_id.split(":")
        type_name = parts[1]  # mounts or minions
        lodestone_id = parts[2]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the character
                query = """
                    SELECT id, name, server, lodestone_id, discord_user_id
                    FROM characters
                    WHERE lodestone_id = $1
                    LIMIT 1
                """
                result = await session.execute(query, lodestone_id)
                char = await result.fetchone()
                
                if not char:
                    return await ctx.edit_origin(
                        content="Character not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Get progress message
                progress_embed = Embed(
                    title=f"Getting Recommendations",
                    description=f"Analyzing {type_name} collection for {char['name']} ({char['server']})...",
                    color=0x3498db
                )
                await ctx.edit_origin(embed=progress_embed, components=[])
                
                # Get recommendations
                if type_name == "mounts":
                    recommendations = await self.recommendation_engine.get_mount_recommendations(lodestone_id, count=5)
                else:  # minions
                    recommendations = await self.recommendation_engine.get_minion_recommendations(lodestone_id, count=5)
                
                # Create embed response
                embed = Embed(
                    title=f"Recommended {type_name.capitalize()} to Farm",
                    description=f"For **{char['name']}** ({char['server']})",
                    color=0x2ecc71
                )
                
                if not recommendations:
                    embed.add_field(
                        name="No Recommendations",
                        value="No farmable items found that match your character's progression.",
                        inline=False
                    )
                else:
                    for i, item in enumerate(recommendations):
                        # Format source information
                        sources_text = ""
                        for source in item.get('sources', []):
                            source_type = source.get('type', '')
                            if source_type in ['Dungeon', 'Trial', 'Raid', 'Alliance Raid', 'FATE']:
                                duty_name = source.get('duty_name', '')
                                duty_level = source.get('duty_level', 0)
                                
                                if duty_name:
                                    sources_text += f"• {source_type}: {duty_name}"
                                    if duty_level:
                                        sources_text += f" (Level {duty_level})"
                                    sources_text += "\n"
                                else:
                                    text = source.get('text', '')
                                    sources_text += f"• {source_type}: {text}\n"
                                
                                # Add drop rate if available
                                drop_rate = source.get('drop_rate')
                                if drop_rate is not None:
                                    if drop_rate > 0:
                                        sources_text += f"  Drop Rate: {drop_rate}%\n"
                                    else:
                                        sources_text += f"  Drop Rate: Unknown\n"
                        
                        # Add description if available
                        description = item.get('description', '')
                        if description:
                            description = f"{description}\n\n"
                        
                        embed.add_field(
                            name=f"{i+1}. {item['name']}",
                            value=f"{description}{sources_text}" if sources_text else "No source information available",
                            inline=False
                        )
                
                # Add buttons for actions
                components = [
                    ActionRow(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="View Missing Items",
                            custom_id=f"view_more_missing:{type_name}:{lodestone_id}:0"
                        )
                    )
                ]
                
                # Update the message
                await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return await ctx.edit_origin(
                content="An error occurred while generating recommendations. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @farm_command.subcommand(
        sub_cmd_name="search",
        sub_cmd_description="Search for a mount or minion",
    )
    @slash_option(
        name="type",
        description="What to search for",
        required=True,
        opt_type=OptionType.STRING,
        choices=[
            {"name": "Mount", "value": "mount"},
            {"name": "Minion", "value": "minion"}
        ]
    )
    @slash_option(
        name="name",
        description="Name to search for",
        required=True,
        opt_type=OptionType.STRING
    )
    async def farm_search(self, ctx: SlashContext, type: str, name: str):
        """Search for a mount or minion."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Search for items
            if type == "mount":
                results = await self.ffxivcollect.search_mounts(name)
            else:  # minion
                results = await self.ffxivcollect.search_minions(name)
            
            if not results:
                return await ctx.send(f"No {type}s found matching '{name}'.")
            
            # Create embed response
            embed = Embed(
                title=f"{type.capitalize()} Search Results",
                description=f"Found {len(results)} {type}(s) matching '{name}'.",
                color=0x3498db
            )
            
            # Only show the first 5 results in detail
            for i, item in enumerate(results[:5]):
                # Format source information
                sources_text = ""
                
                for source in item.get('sources', []):
                    source_type = source.get('type', '')
                    text = source.get('text', '')
                    
                    sources_text += f"• {source_type}: {text}\n"
                
                # Format item description
                description = item.get('description', '')
                if description:
                    description = f"{description}\n\n"
                
                embed.add_field(
                    name=f"{i+1}. {item['name']}",
                    value=f"{description}{sources_text}" if sources_text else "No source information available",
                    inline=False
                )
            
            # If there are more results, mention them
            if len(results) > 5:
                embed.set_footer(text=f"Showing 5/{len(results)} results. Refine your search for more specific results.")
            
            return await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error searching for {type}s: {e}")
            return await ctx.send(f"An error occurred while searching. Please try again later.")

# Setup function to register the extension
async def setup(client: Client) -> Extension:
    """Set up the Farming extension."""
    return FarmingCog(client)