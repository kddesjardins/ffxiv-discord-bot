"""
MSQ Progression tracking commands for the FFXIV Discord bot.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

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
    Modal,
    TextInput,
    TextStyleType,
    ModalContext,
    listen,
    Member,
    Role
)
import asyncpg

from services.xivapi import XIVAPI
from utils.db import get_db_session
from utils.logging import get_logger

# Logger
logger = get_logger()

# MSQ expansion information
MSQ_EXPANSIONS = [
    {"id": 2, "name": "A Realm Reborn", "abbr": "ARR", "level_range": "1-50", "color": 0xab0000},
    {"id": 3, "name": "Heavensward", "abbr": "HW", "level_range": "50-60", "color": 0x3a50ba},
    {"id": 4, "name": "Stormblood", "abbr": "SB", "level_range": "60-70", "color": 0xcc3333},
    {"id": 5, "name": "Shadowbringers", "abbr": "ShB", "level_range": "70-80", "color": 0x9370db},
    {"id": 6, "name": "Endwalker", "abbr": "EW", "level_range": "80-90", "color": 0xffd700},
    {"id": 7, "name": "Dawntrail", "abbr": "DT", "level_range": "90-100", "color": 0xff7f50}
]

# Content unlocked by MSQ progress
MSQ_CONTENT_UNLOCKS = [
    # ARR
    {"expansion": 2, "min_progress": 0, "name": "Sastasha", "type": "Dungeon", "level": 15},
    {"expansion": 2, "min_progress": 25, "name": "Tam-Tara Deepcroft", "type": "Dungeon", "level": 16},
    {"expansion": 2, "min_progress": 25, "name": "Copperbell Mines", "type": "Dungeon", "level": 17},
    {"expansion": 2, "min_progress": 50, "name": "The Thousand Maws of Toto-Rak", "type": "Dungeon", "level": 24},
    {"expansion": 2, "min_progress": 50, "name": "Haukke Manor", "type": "Dungeon", "level": 28},
    {"expansion": 2, "min_progress": 50, "name": "Brayflox's Longstop", "type": "Dungeon", "level": 32},
    {"expansion": 2, "min_progress": 75, "name": "The Stone Vigil", "type": "Dungeon", "level": 41},
    {"expansion": 2, "min_progress": 75, "name": "Dzemael Darkhold", "type": "Dungeon", "level": 44},
    {"expansion": 2, "min_progress": 75, "name": "The Aurum Vale", "type": "Dungeon", "level": 47},
    {"expansion": 2, "min_progress": 100, "name": "Cape Westwind", "type": "Trial", "level": 49},
    {"expansion": 2, "min_progress": 100, "name": "Castrum Meridianum", "type": "Dungeon", "level": 50},
    {"expansion": 2, "min_progress": 100, "name": "The Praetorium", "type": "Dungeon", "level": 50},
    # HW
    {"expansion": 3, "min_progress": 0, "name": "The Dusk Vigil", "type": "Dungeon", "level": 51},
    {"expansion": 3, "min_progress": 25, "name": "The Aery", "type": "Dungeon", "level": 55},
    {"expansion": 3, "min_progress": 50, "name": "The Vault", "type": "Dungeon", "level": 57},
    {"expansion": 3, "min_progress": 75, "name": "The Great Gubal Library", "type": "Dungeon", "level": 59},
    {"expansion": 3, "min_progress": 100, "name": "The Aetherochemical Research Facility", "type": "Dungeon", "level": 60},
    # SB
    {"expansion": 4, "min_progress": 0, "name": "The Sirensong Sea", "type": "Dungeon", "level": 61},
    {"expansion": 4, "min_progress": 25, "name": "Bardam's Mettle", "type": "Dungeon", "level": 65},
    {"expansion": 4, "min_progress": 50, "name": "Doma Castle", "type": "Dungeon", "level": 67},
    {"expansion": 4, "min_progress": 75, "name": "Castrum Abania", "type": "Dungeon", "level": 69},
    {"expansion": 4, "min_progress": 100, "name": "Ala Mhigo", "type": "Dungeon", "level": 70},
    # ShB
    {"expansion": 5, "min_progress": 25, "name": "Holminster Switch", "type": "Dungeon", "level": 71},
    {"expansion": 5, "min_progress": 50, "name": "Dohn Mheg", "type": "Dungeon", "level": 73},
    {"expansion": 5, "min_progress": 50, "name": "The Qitana Ravel", "type": "Dungeon", "level": 75},
    {"expansion": 5, "min_progress": 75, "name": "Malikah's Well", "type": "Dungeon", "level": 77},
    {"expansion": 5, "min_progress": 75, "name": "Mt. Gulg", "type": "Dungeon", "level": 79},
    {"expansion": 5, "min_progress": 100, "name": "Amaurot", "type": "Dungeon", "level": 80},
    # EW
    {"expansion": 6, "min_progress": 25, "name": "The Tower of Zot", "type": "Dungeon", "level": 81},
    {"expansion": 6, "min_progress": 50, "name": "The Tower of Babil", "type": "Dungeon", "level": 83},
    {"expansion": 6, "min_progress": 50, "name": "Vanaspati", "type": "Dungeon", "level": 85},
    {"expansion": 6, "min_progress": 75, "name": "Ktisis Hyperboreia", "type": "Dungeon", "level": 87},
    {"expansion": 6, "min_progress": 100, "name": "The Aitiascope", "type": "Dungeon", "level": 89},
    {"expansion": 6, "min_progress": 100, "name": "The Mothercrystal", "type": "Trial", "level": 90},
    # DT
    {"expansion": 7, "min_progress": 25, "name": "The Lynx Valley", "type": "Dungeon", "level": 91},
    {"expansion": 7, "min_progress": 50, "name": "The Aqueduct of Az'aqar", "type": "Dungeon", "level": 93},
    {"expansion": 7, "min_progress": 75, "name": "The Voidcast Dais", "type": "Trial", "level": 95},
    {"expansion": 7, "min_progress": 100, "name": "The Hidden Tunnels of Tulla", "type": "Dungeon", "level": 97},
    {"expansion": 7, "min_progress": 100, "name": "Solution Nine", "type": "Dungeon", "level": 99}
]

class ProgressionCog(Extension):
    """MSQ Progression tracking commands."""
    
    def __init__(self, client: Client):
        self.client = client
        self.xivapi = XIVAPI()
    
    @slash_command(
        name="msq",
        description="MSQ progression commands",
    )
    async def msq_command(self, ctx: SlashContext):
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
    @slash_option(
        name="character",
        description="Character to update (defaults to primary)",
        required=False,
        opt_type=OptionType.STRING
    )
    async def msq_update(self, ctx: SlashContext, expansion: str, progress: str, character: str = None):
        """Update MSQ progression for a character."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Find the character (primary if not specified)
                if character:
                    # Try to find by name first
                    query = """
                        SELECT id, name, server, lodestone_id
                        FROM characters
                        WHERE name ILIKE $1 AND discord_user_id = $2
                        LIMIT 1
                    """
                    result = await session.execute(query, character, str(ctx.author.id))
                    char = await result.fetchone()
                    
                    if not char:
                        # Try by Lodestone ID
                        query = """
                            SELECT id, name, server, lodestone_id
                            FROM characters
                            WHERE lodestone_id = $1 AND discord_user_id = $2
                            LIMIT 1
                        """
                        result = await session.execute(query, character, str(ctx.author.id))
                        char = await result.fetchone()
                        
                        if not char:
                            return await ctx.send(f"Character '{character}' not found or not owned by you. Please register it first with `/character register`.")
                else:
                    # Get primary character
                    query = """
                        SELECT id, name, server, lodestone_id
                        FROM characters
                        WHERE discord_user_id = $1 AND is_primary = TRUE
                        LIMIT 1
                    """
                    result = await session.execute(query, str(ctx.author.id))
                    char = await result.fetchone()
                    
                    if not char:
                        return await ctx.send("No primary character found. Please register a character with `/character register` or specify a character name.")
                
                # Map expansion shorthand to ID
                expansion_map = {
                    "arr": 2,
                    "hw": 3,
                    "sb": 4,
                    "shb": 5,
                    "ew": 6,
                    "dt": 7
                }
                
                expansion_id = expansion_map.get(expansion)
                expansion_info = next((e for e in MSQ_EXPANSIONS if e["id"] == expansion_id), None)
                
                if not expansion_info:
                    return await ctx.send(f"Invalid expansion: {expansion}")
                
                # Map progress to percentage
                progress_map = {
                    "started": 0,
                    "25pct": 25,
                    "50pct": 50,
                    "75pct": 75,
                    "complete": 100,
                    "patches": 100  # We'll handle patches specially
                }
                
                completion_percentage = progress_map.get(progress)
                
                # Create/update progress record
                # First check if there's an existing progress record
                query = """
                    SELECT id, progress_type, content_name, status, completion_percentage
                    FROM character_progress
                    WHERE character_id = $1 AND progress_type = 'msq' AND content_name = $2
                """
                result = await session.execute(query, char['id'], expansion_info['name'])
                existing_progress = await result.fetchone()
                
                # Format the status text
                if progress == "patches":
                    status_text = "completed_patches"
                    display_status = f"Completed {expansion_info['name']} + Patch Content"
                elif progress == "complete":
                    status_text = "completed"
                    display_status = f"Completed {expansion_info['name']} Main Story"
                else:
                    status_text = "in_progress"
                    display_status = f"{expansion_info['name']} ({completion_percentage}% Complete)"
                
                # Update or insert the progress record
                if existing_progress:
                    query = """
                        UPDATE character_progress
                        SET status = $1, completion_percentage = $2, updated_at = $3
                        WHERE id = $4
                        RETURNING id
                    """
                    result = await session.execute(
                        query,
                        status_text,
                        completion_percentage,
                        datetime.utcnow(),
                        existing_progress['id']
                    )
                else:
                    query = """
                        INSERT INTO character_progress (
                            character_id, progress_type, content_name, content_id, 
                            status, current_step, completion_percentage
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id
                    """
                    result = await session.execute(
                        query,
                        char['id'],
                        'msq',
                        expansion_info['name'],
                        expansion_info['id'],
                        status_text,
                        f"{expansion_info['name']} MSQ",
                        completion_percentage
                    )
                
                # Log the MSQ progression in character's record too
                # This helps with quick lookups for recommendations
                query = """
                    UPDATE characters
                    SET msq_progress = $1, msq_id = $2
                    WHERE id = $3
                """
                await session.execute(
                    query,
                    display_status,
                    expansion_info['id'],
                    char['id']
                )
                
                # Create embed response
                embed = Embed(
                    title="MSQ Progress Updated",
                    description=f"Updated MSQ progress for **{char['name']}** ({char['server']})",
                    color=expansion_info['color']
                )
                
                embed.add_field(name="Expansion", value=expansion_info['name'], inline=True)
                embed.add_field(name="Level Range", value=expansion_info['level_range'], inline=True)
                embed.add_field(name="Status", value=display_status, inline=True)
                
                # Add buttons for next steps
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="View Progress",
                        custom_id=f"view_msq_progress:{char['id']}"
                    ),
                    Button(
                        style=ButtonStyle.SUCCESS,
                        label="Get Recommendations",
                        custom_id=f"get_msq_recommendations:{char['id']}"
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error updating MSQ progress: {e}")
            return await ctx.send(f"An error occurred while updating MSQ progress. Please try again later.")
    
    @msq_command.subcommand(
        sub_cmd_name="view",
        sub_cmd_description="View MSQ progression for a character",
    )
    @slash_option(
        name="character",
        description="Character to view (defaults to primary)",
        required=False,
        opt_type=OptionType.STRING
    )
    async def msq_view(self, ctx: SlashContext, character: str = None):
        """View MSQ progression for a character."""
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
                        WHERE name ILIKE $1
                        LIMIT 1
                    """
                    result = await session.execute(query, character)
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
                    # For simplicity, we'll allow viewing anyone's progress
                    # In a real implementation, you might want to check permissions
                    character_owner = f"<@{char['discord_user_id']}>"
                else:
                    character_owner = None
                
                # Get all MSQ progress records for this character
                query = """
                    SELECT p.progress_type, p.content_name, p.content_id, 
                           p.status, p.completion_percentage, p.updated_at
                    FROM character_progress p
                    WHERE p.character_id = $1 AND p.progress_type = 'msq'
                    ORDER BY p.content_id ASC
                """
                result = await session.execute(query, char['id'])
                progress_records = await result.fetchall()
                
                # Create embed response
                embed = Embed(
                    title=f"MSQ Progress for {char['name']}",
                    description=f"Character: **{char['name']}** ({char['server']})",
                    color=0x3498db
                )
                
                if character_owner:
                    embed.add_field(name="Character Owner", value=character_owner, inline=True)
                
                # Add fields for each expansion
                has_progress = False
                highest_expansion = 0
                highest_complete = 0
                
                for expansion in MSQ_EXPANSIONS:
                    # Find progress record for this expansion
                    progress = next((p for p in progress_records if p['content_name'] == expansion['name']), None)
                    
                    if progress:
                        has_progress = True
                        
                        # Format status display
                        if progress['status'] == 'completed_patches':
                            status_display = "✅ Completed + Patches"
                            highest_complete = max(highest_complete, expansion['id'])
                            highest_expansion = max(highest_expansion, expansion['id'])
                        elif progress['status'] == 'completed':
                            status_display = "✅ Main Story Complete"
                            highest_complete = max(highest_complete, expansion['id'])
                            highest_expansion = max(highest_expansion, expansion['id'])
                        else:  # in_progress
                            status_display = f"🔄 {progress['completion_percentage']}% Complete"
                            highest_expansion = max(highest_expansion, expansion['id'])
                        
                        # Add when it was updated
                        if progress['updated_at']:
                            updated = progress['updated_at'].strftime("%Y-%m-%d")
                            status_display += f" (Updated: {updated})"
                    else:
                        # Determine if this expansion should be locked or not
                        if expansion['id'] <= highest_complete + 1:
                            status_display = "❌ Not Started"
                        else:
                            status_display = "🔒 Locked (Complete Previous MSQ)"
                    
                    embed.add_field(
                        name=f"{expansion['name']} ({expansion['level_range']})",
                        value=status_display,
                        inline=False
                    )
                
                if not has_progress:
                    embed.add_field(
                        name="No Progress Recorded",
                        value="This character hasn't recorded any MSQ progress yet. Use `/msq update` to set progress.",
                        inline=False
                    )
                
                # Add buttons for actions
                components = []
                
                # Only allow updating if it's your character
                if char['discord_user_id'] == str(ctx.author.id):
                    # Figure out what the next logical expansion to update would be
                    next_expansion = None
                    for expansion in MSQ_EXPANSIONS:
                        if expansion['id'] == highest_expansion + 1:
                            next_expansion = expansion['abbr'].lower()
                            break
                    
                    # If we're in the middle of an expansion, suggest updating that
                    if highest_expansion > highest_complete:
                        for expansion in MSQ_EXPANSIONS:
                            if expansion['id'] == highest_expansion:
                                next_expansion = expansion['abbr'].lower()
                                break
                    
                    # If we have a suggestion, add update button
                    if next_expansion:
                        components.append(
                            ActionRow(
                                Button(
                                    style=ButtonStyle.PRIMARY,
                                    label="Update Progress",
                                    custom_id=f"update_msq_progress:{char['id']}:{next_expansion}"
                                )
                            )
                        )
                
                # Add recommendation button
                components.append(
                    ActionRow(
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Get Recommendations",
                            custom_id=f"get_msq_recommendations:{char['id']}"
                        )
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error viewing MSQ progress: {e}")
            return await ctx.send(f"An error occurred while retrieving MSQ progress. Please try again later.")
    
    @component_callback("view_msq_progress")
    async def view_msq_progress_callback(self, ctx: ComponentContext):
        """Handle viewing MSQ progress via button."""
        # Get character ID from button custom ID
        char_id = ctx.custom_id.split(":")[1]
        
        # Create a new context-like object to trigger the view command
        # Simply reusing the handler itself is easier
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Get character information
                query = """
                    SELECT id, name, server, lodestone_id, discord_user_id
                    FROM characters
                    WHERE id = $1
                    LIMIT 1
                """
                result = await session.execute(query, char_id)
                char = await result.fetchone()
                
                if not char:
                    return await ctx.edit_origin(
                        content="Character not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Now proceed with msq_view logic
                # Get all MSQ progress records for this character
                query = """
                    SELECT p.progress_type, p.content_name, p.content_id, 
                           p.status, p.completion_percentage, p.updated_at
                    FROM character_progress p
                    WHERE p.character_id = $1 AND p.progress_type = 'msq'
                    ORDER BY p.content_id ASC
                """
                result = await session.execute(query, char['id'])
                progress_records = await result.fetchall()
                
                # Create embed response
                embed = Embed(
                    title=f"MSQ Progress for {char['name']}",
                    description=f"Character: **{char['name']}** ({char['server']})",
                    color=0x3498db
                )
                
                if char['discord_user_id'] != str(ctx.author.id):
                    embed.add_field(name="Character Owner", value=f"<@{char['discord_user_id']}>", inline=True)
                
                # Add fields for each expansion
                has_progress = False
                highest_expansion = 0
                highest_complete = 0
                
                for expansion in MSQ_EXPANSIONS:
                    # Find progress record for this expansion
                    progress = next((p for p in progress_records if p['content_name'] == expansion['name']), None)
                    
                    if progress:
                        has_progress = True
                        
                        # Format status display
                        if progress['status'] == 'completed_patches':
                            status_display = "✅ Completed + Patches"
                            highest_complete = max(highest_complete, expansion['id'])
                            highest_expansion = max(highest_expansion, expansion['id'])
                        elif progress['status'] == 'completed':
                            status_display = "✅ Main Story Complete"
                            highest_complete = max(highest_complete, expansion['id'])
                            highest_expansion = max(highest_expansion, expansion['id'])
                        else:  # in_progress
                            status_display = f"🔄 {progress['completion_percentage']}% Complete"
                            highest_expansion = max(highest_expansion, expansion['id'])
                        
                        # Add when it was updated
                        if progress['updated_at']:
                            updated = progress['updated_at'].strftime("%Y-%m-%d")
                            status_display += f" (Updated: {updated})"
                    else:
                        # Determine if this expansion should be locked or not
                        if expansion['id'] <= highest_complete + 1:
                            status_display = "❌ Not Started"
                        else:
                            status_display = "🔒 Locked (Complete Previous MSQ)"
                    
                    embed.add_field(
                        name=f"{expansion['name']} ({expansion['level_range']})",
                        value=status_display,
                        inline=False
                    )
                
                if not has_progress:
                    embed.add_field(
                        name="No Progress Recorded",
                        value="This character hasn't recorded any MSQ progress yet. Use `/msq update` to set progress.",
                        inline=False
                    )
                
                # Add buttons for actions
                components = []
                
                # Only allow updating if it's your character
                if char['discord_user_id'] == str(ctx.author.id):
                    # Figure out what the next logical expansion to update would be
                    next_expansion = None
                    for expansion in MSQ_EXPANSIONS:
                        if expansion['id'] == highest_expansion + 1:
                            next_expansion = expansion['abbr'].lower()
                            break
                    
                    # If we're in the middle of an expansion, suggest updating that
                    if highest_expansion > highest_complete:
                        for expansion in MSQ_EXPANSIONS:
                            if expansion['id'] == highest_expansion:
                                next_expansion = expansion['abbr'].lower()
                                break
                    
                    # If we have a suggestion, add update button
                    if next_expansion:
                        components.append(
                            ActionRow(
                                Button(
                                    style=ButtonStyle.PRIMARY,
                                    label="Update Progress",
                                    custom_id=f"update_msq_progress:{char['id']}:{next_expansion}"
                                )
                            )
                        )
                
                # Add recommendation button
                components.append(
                    ActionRow(
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Get Recommendations",
                            custom_id=f"get_msq_recommendations:{char['id']}"
                        )
                    )
                )
                
                # Update the message
                await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error viewing MSQ progress: {e}")
            return await ctx.edit_origin(
                content="An error occurred while retrieving MSQ progress. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @component_callback("update_msq_progress")
    async def update_msq_progress_callback(self, ctx: ComponentContext):
        """Handle updating MSQ progress via button."""
        # Get parameters from button custom ID
        parts = ctx.custom_id.split(":")
        char_id = parts[1]
        expansion = parts[2] if len(parts) > 2 else None
        
        # Create modal for MSQ progress update
        modal = Modal(
            title="Update MSQ Progress",
            custom_id=f"msq_progress_modal:{char_id}:{expansion}",
            components=[
                TextInput(
                    style=TextStyleType.SHORT,
                    label="Current Expansion",
                    custom_id="expansion",
                    placeholder="Enter expansion (arr, hw, sb, shb, ew, dt)",
                    min_length=2,
                    max_length=4,
                    required=True,
                    default=expansion
                ),
                TextInput(
                    style=TextStyleType.SHORT,
                    label="Progress",
                    custom_id="progress",
                    placeholder="started, 25pct, 50pct, 75pct, complete, patches",
                    min_length=5,
                    max_length=8,
                    required=True
                )
            ]
        )
        
        await ctx.popup(modal)
    
    @listen("modal_submit")
    async def on_modal_submit(self, ctx: ModalContext):
        """Handle modal submissions."""
        if ctx.custom_id.startswith("msq_progress_modal"):
            # Extract character ID from custom ID
            parts = ctx.custom_id.split(":")
            char_id = parts[1]
            
            # Get form data
            expansion = ctx.responses.get("expansion", "").lower()
            progress = ctx.responses.get("progress", "").lower()
            
            # Validate inputs
            valid_expansions = ["arr", "hw", "sb", "shb", "ew", "dt"]
            valid_progress = ["started", "25pct", "50pct", "75pct", "complete", "patches"]
            
            if expansion not in valid_expansions:
                return await ctx.send(f"Invalid expansion '{expansion}'. Please use one of: {', '.join(valid_expansions)}", ephemeral=True)
            
            if progress not in valid_progress:
                return await ctx.send(f"Invalid progress '{progress}'. Please use one of: {', '.join(valid_progress)}", ephemeral=True)
            
            try:
                async with get_db_session() as session:
                    # Get character information
                    query = """
                        SELECT id, name, server, lodestone_id, discord_user_id
                        FROM characters
                        WHERE id = $1
                        LIMIT 1
                    """
                    result = await session.execute(query, char_id)
                    char = await result.fetchone()
                    
                    if not char:
                        return await ctx.send("Character not found or deleted.", ephemeral=True)
                    
                    # Verify ownership
                    if char['discord_user_id'] != str(ctx.author.id):
                        return await ctx.send("You don't have permission to update this character's progress.", ephemeral=True)
                    
                    # Defer response while we process
                    await ctx.defer()
                    
                    # Now process the update
                    # Map expansion shorthand to ID
                    expansion_map = {
                        "arr": 2,
                        "hw": 3,
                        "sb": 4,
                        "shb": 5,
                        "ew": 6,
                        "dt": 7
                    }
                    
                    expansion_id = expansion_map.get(expansion)
                    expansion_info = next((e for e in MSQ_EXPANSIONS if e["id"] == expansion_id), None)
                    
                    # Map progress to percentage
                    progress_map = {
                        "started": 0,
                        "25pct": 25,
                        "50pct": 50,
                        "75pct": 75,
                        "complete": 100,
                        "patches": 100  # We'll handle patches specially
                    }
                    
                    completion_percentage = progress_map.get(progress)
                    
                    # Format status text
                    if progress == "patches":
                        status_text = "completed_patches"
                        display_status = f"Completed {expansion_info['name']} + Patch Content"
                    elif progress == "complete":
                        status_text = "completed"
                        display_status = f"Completed {expansion_info['name']} Main Story"
                    else:
                        status_text = "in_progress"
                        display_status = f"{expansion_info['name']} ({completion_percentage}% Complete)"
                    
                    # Check for existing progress record
                    query = """
                        SELECT id, progress_type, content_name, status, completion_percentage
                        FROM character_progress
                        WHERE character_id = $1 AND progress_type = 'msq' AND content_name = $2
                    """
                    result = await session.execute(query, char['id'], expansion_info['name'])
                    existing_progress = await result.fetchone()
                    
                    # Update or insert progress record
                    if existing_progress:
                        query = """
                            UPDATE character_progress
                            SET status = $1, completion_percentage = $2, updated_at = $3
                            WHERE id = $4
                            RETURNING id
                        """
                        result = await session.execute(
                            query,
                            status_text,
                            completion_percentage,
                            datetime.utcnow(),
                            existing_progress['id']
                        )
                    else:
                        query = """
                            INSERT INTO character_progress (
                                character_id, progress_type, content_name, content_id, 
                                status, current_step, completion_percentage
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            RETURNING id
                        """
                        result = await session.execute(
                            query,
                            char['id'],
                            'msq',
                            expansion_info['name'],
                            expansion_info['id'],
                            status_text,
                            f"{expansion_info['name']} MSQ",
                            completion_percentage
                        )
                    
                    # Update character record
                    query = """
                        UPDATE characters
                        SET msq_progress = $1, msq_id = $2
                        WHERE id = $3
                    """
                    await session.execute(
                        query,
                        display_status,
                        expansion_info['id'],
                        char['id']
                    )
                    
                    # Create response
                    embed = Embed(
                        title="MSQ Progress Updated",
                        description=f"Updated MSQ progress for **{char['name']}** ({char['server']})",
                        color=expansion_info['color']
                    )
                    
                    embed.add_field(name="Expansion", value=expansion_info['name'], inline=True)
                    embed.add_field(name="Level Range", value=expansion_info['level_range'], inline=True)
                    embed.add_field(name="Status", value=display_status, inline=True)
                    
                    # Add buttons for next steps
                    components = ActionRow(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="View Progress",
                            custom_id=f"view_msq_progress:{char['id']}"
                        ),
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Get Recommendations",
                            custom_id=f"get_msq_recommendations:{char['id']}"
                        )
                    )
                    
                    return await ctx.send(embed=embed, components=components)
                    
            except Exception as e:
                logger.error(f"Error updating MSQ progress: {e}")
                return await ctx.send(f"An error occurred while updating MSQ progress. Please try again later.")
    
    @component_callback("get_msq_recommendations")
    async def get_msq_recommendations_callback(self, ctx: ComponentContext):
        """Handle getting MSQ-based recommendations."""
        # Get character ID from button custom ID
        char_id = ctx.custom_id.split(":")[1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Get character information
                query = """
                    SELECT id, name, server, lodestone_id, discord_user_id, msq_id
                    FROM characters
                    WHERE id = $1
                    LIMIT 1
                """
                result = await session.execute(query, char_id)
                char = await result.fetchone()
                
                if not char:
                    return await ctx.edit_origin(
                        content="Character not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Get MSQ progress records for this character
                query = """
                    SELECT p.progress_type, p.content_name, p.content_id, 
                           p.status, p.completion_percentage, p.updated_at
                    FROM character_progress p
                    WHERE p.character_id = $1 AND p.progress_type = 'msq'
                    ORDER BY p.content_id DESC
                    LIMIT 1
                """
                result = await session.execute(query, char['id'])
                progress = await result.fetchone()
                
                if not progress:
                    # No MSQ progress recorded, default to beginning
                    msq_expansion = 2  # ARR
                    msq_completion = 0
                    expansion_name = "A Realm Reborn"
                else:
                    msq_expansion = progress['content_id']
                    msq_completion = progress['completion_percentage']
                    expansion_name = progress['content_name']
                    
                    # Handle special status
                    if progress['status'] == 'completed_patches':
                        # If completed with patches, can access content from next expansion
                        if msq_expansion < 7:  # Not Dawntrail
                            msq_expansion += 1
                            msq_completion = 0
                            expansion_info = next((e for e in MSQ_EXPANSIONS if e["id"] == msq_expansion), None)
                            expansion_name = expansion_info['name']
                
                # Find content recommendations based on MSQ progress
                available_content = []
                for content in MSQ_CONTENT_UNLOCKS:
                    # Content is available if:
                    # 1. It's from an earlier expansion that's completed
                    # 2. It's from the current expansion and we've reached the required % completion
                    if (content['expansion'] < msq_expansion) or \
                       (content['expansion'] == msq_expansion and content['min_progress'] <= msq_completion):
                        available_content.append(content)
                
                # Create embed response
                embed = Embed(
                    title=f"MSQ-Based Recommendations for {char['name']}",
                    description=(
                        f"Based on your MSQ progress in **{expansion_name}** "
                        f"({msq_completion}% complete)"),
                    color=0x3498db
                )
                
                if char['discord_user_id'] != str(ctx.author.id):
                    embed.add_field(name="Character Owner", value=f"<@{char['discord_user_id']}>", inline=True)
                
                # Group content by expansion
                expansion_content = {}
                for content in available_content:
                    exp_id = content['expansion']
                    if exp_id not in expansion_content:
                        expansion_content[exp_id] = []
                    expansion_content[exp_id].append(content)
                
                # Add content recommendations by expansion
                for exp_id, content_list in expansion_content.items():
                    expansion_info = next((e for e in MSQ_EXPANSIONS if e["id"] == exp_id), None)
                    
                    # Sort content by level
                    content_list.sort(key=lambda x: x['level'])
                    
                    # Format content list
                    content_text = ""
                    for content in content_list[-5:]:  # Show last 5 (newest) from each expansion
                        content_text += f"• {content['name']} ({content['type']}, Lv. {content['level']})\n"
                    
                    if content_text:
                        embed.add_field(
                            name=f"{expansion_info['name']} Content",
                            value=content_text,
                            inline=False
                        )
                
                # Add note about unlocking more content
                if msq_expansion <= 7:  # Not finished with Dawntrail
                    next_expansion = msq_expansion
                    if msq_completion >= 100:
                        # If at 100%, suggest next expansion if not Dawntrail
                        if msq_expansion < 7:
                            next_expansion = msq_expansion + 1
                    
                    next_expansion_info = next((e for e in MSQ_EXPANSIONS if e["id"] == next_expansion), None)
                    
                    if next_expansion_info:
                        # Get next progress milestone
                        next_milestone = None
                        if msq_completion < 25:
                            next_milestone = 25
                        elif msq_completion < 50:
                            next_milestone = 50
                        elif msq_completion < 75:
                            next_milestone = 75
                        elif msq_completion < 100:
                            next_milestone = 100
                        
                        if next_milestone:
                            # Find content unlocked at next milestone
                            next_content = [c for c in MSQ_CONTENT_UNLOCKS if c['expansion'] == msq_expansion and c['min_progress'] == next_milestone]
                            
                            if next_content:
                                unlock_text = ", ".join([f"{c['name']} ({c['type']})" for c in next_content])
                                embed.add_field(
                                    name=f"Next Unlocks at {next_milestone}% in {next_expansion_info['name']}",
                                    value=f"Continue the MSQ to unlock: {unlock_text}",
                                    inline=False
                                )
                
                # Add buttons for actions
                components = [
                    ActionRow(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="View Progress",
                            custom_id=f"view_msq_progress:{char['id']}"
                        ),
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Update Progress",
                            custom_id=f"update_msq_progress:{char['id']}:{next((e for e in MSQ_EXPANSIONS if e['id'] == msq_expansion), {'abbr': 'arr'})['abbr'].lower()}"
                        )
                    )
                ]
                
                # Update the message
                await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error getting MSQ recommendations: {e}")
            return await ctx.edit_origin(
                content="An error occurred while retrieving MSQ recommendations. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @msq_command.subcommand(
        sub_cmd_name="recommendations",
        sub_cmd_description="Get content recommendations based on MSQ progress",
    )
    @slash_option(
        name="character",
        description="Character to get recommendations for (defaults to primary)",
        required=False,
        opt_type=OptionType.STRING
    )
    async def msq_recommendations(self, ctx: SlashContext, character: str = None):
        """Get MSQ-based content recommendations."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Find the character (primary if not specified)
                if character:
                    # Try to find by name first
                    query = """
                        SELECT id, name, server, lodestone_id, discord_user_id, msq_id
                        FROM characters
                        WHERE name ILIKE $1
                        LIMIT 1
                    """
                    result = await session.execute(query, character)
                    char = await result.fetchone()
                    
                    if not char:
                        # Try by Lodestone ID
                        query = """
                            SELECT id, name, server, lodestone_id, discord_user_id, msq_id
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
                        SELECT id, name, server, lodestone_id, discord_user_id, msq_id
                        FROM characters
                        WHERE discord_user_id = $1 AND is_primary = TRUE
                        LIMIT 1
                    """
                    result = await session.execute(query, str(ctx.author.id))
                    char = await result.fetchone()
                    
                    if not char:
                        return await ctx.send("No primary character found. Please register a character with `/character register` or specify a character name.")
                
                # Create a ComponentContext-like object to reuse the callback
                new_ctx = ctx
                new_ctx.custom_id = f"get_msq_recommendations:{char['id']}"
                await self.get_msq_recommendations_callback(new_ctx)
                
        except Exception as e:
            logger.error(f"Error getting MSQ recommendations: {e}")
            return await ctx.send(f"An error occurred while retrieving MSQ recommendations. Please try again later.")

# Setup function to register the extension
async def setup(client: Client) -> Extension:
    """Set up the Progression extension."""
    return ProgressionCog(client)