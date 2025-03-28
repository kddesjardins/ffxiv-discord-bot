"""
Group management commands for the FFXIV Discord bot.
"""
import logging
from typing import Dict, Any, List, Optional
import uuid

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
from interactions.models.discord.components import TextInput
import asyncpg

from models.character import Character
from models.group import Group
from services.xivapi import XIVAPI
from services.recommendation import RecommendationEngine
from services.ffxivcollect import FFXIVCollectAPI
from utils.db import get_db_session
from utils.logging import get_logger

# Logger
logger = get_logger()

class GroupsCog(Extension):
    """Group management commands."""
    
    def __init__(self, client: Client):
        self.client = client
        self.xivapi = XIVAPI()
        self.ffxivcollect = FFXIVCollectAPI()
        self.recommendation_engine = RecommendationEngine(self.ffxivcollect, self.xivapi)
    
    @slash_command(
        name="group",
        description="Group management commands",
    )
    async def group_command(self, ctx: SlashContext):
        """Group management command group."""
        # This is a command group and doesn't need its own implementation
        pass
    
    @group_command.subcommand(
        sub_cmd_name="create",
        sub_cmd_description="Create a new character group",
    )
    @slash_option(
        name="name",
        description="Group name",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="description",
        description="Group description",
        required=False,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="color",
        description="Group color (hex code)",
        required=False,
        opt_type=OptionType.STRING
    )
    async def group_create(
        self, 
        ctx: SlashContext, 
        name: str,
        description: str = None,
        color: str = None
    ):
        """Create a new character group."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Validate input
            if len(name) > 100:
                return await ctx.send("Group name cannot exceed 100 characters.")
            
            if description and len(description) > 500:
                return await ctx.send("Group description cannot exceed 500 characters.")
            
            # Validate color format if provided
            if color:
                color = color.strip().lower()
                if not color.startswith('#'):
                    color = f"#{color}"
                
                # Check if it's a valid hex color
                try:
                    int(color[1:], 16)
                    if len(color) != 7:  # #RRGGBB format
                        raise ValueError("Invalid color format")
                except ValueError:
                    return await ctx.send("Invalid color format. Please use a valid hex color code (e.g., #3498db).")
            
            # Check if group with same name already exists for this guild
            async with get_db_session() as session:
                query = """
                    SELECT id FROM groups
                    WHERE guild_id = $1 AND name ILIKE $2
                """
                result = await session.execute(query, str(ctx.guild_id), name)
                existing = await result.fetchone()
                
                if existing:
                    return await ctx.send(f"A group with the name '{name}' already exists in this server.")
                
                # Create the new group
                query = """
                    INSERT INTO groups (
                        name, description, guild_id, created_by, color
                    ) VALUES (
                        $1, $2, $3, $4, $5
                    ) RETURNING id
                """
                
                result = await session.execute(
                    query,
                    name,
                    description,
                    str(ctx.guild_id),
                    str(ctx.author.id),
                    color
                )
                group_id = await result.fetchone()
                
                # Create embed response
                embed = Embed(
                    title="Group Created",
                    description=f"Successfully created the '{name}' group.",
                    color=int(color[1:], 16) if color else 0x3498db
                )
                
                if description:
                    embed.add_field(name="Description", value=description, inline=False)
                
                embed.add_field(name="Members", value="0", inline=True)
                embed.add_field(name="Created By", value=ctx.author.mention, inline=True)
                
                # Add buttons for next steps
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="Add Characters",
                        custom_id=f"add_characters_to_group:{group_id['id']}"
                    ),
                    Button(
                        style=ButtonStyle.SECONDARY,
                        label="Manage Permissions",
                        custom_id=f"manage_group_permissions:{group_id['id']}"
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return await ctx.send(f"An error occurred while creating the group. Please try again later.")
    
    @group_command.subcommand(
        sub_cmd_name="list",
        sub_cmd_description="List available character groups",
    )
    async def group_list(self, ctx: SlashContext):
        """List available character groups."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Get viewable groups for the user
                # For simplicity, we'll just get all groups for now
                # In a real implementation, you'd check permissions
                query = """
                    SELECT g.id, g.name, g.description, g.color, g.created_by,
                           COUNT(cg.character_id) as member_count
                    FROM groups g
                    LEFT JOIN character_group cg ON g.id = cg.group_id
                    WHERE g.guild_id = $1
                    GROUP BY g.id
                    ORDER BY g.name ASC
                """
                result = await session.execute(query, str(ctx.guild_id))
                groups = await result.fetchall()
                
                if not groups:
                    return await ctx.send("No character groups found. Use `/group create` to create a new group.")
                
                # Create embed response
                embed = Embed(
                    title="FFXIV Character Groups",
                    description=f"Found {len(groups)} group(s) in this server.",
                    color=0x3498db
                )
                
                # Add each group to the embed
                for group in groups:
                    # Get creator name
                    creator = f"<@{group['created_by']}>"
                    
                    # Set color if available
                    color_value = f"{group['color']}" if group['color'] else "Default"
                    
                    # Create field value
                    value = f"Members: {group['member_count']}\n"
                    value += f"Creator: {creator}\n"
                    
                    if group['description']:
                        # Truncate description if too long
                        desc = group['description']
                        if len(desc) > 100:
                            desc = desc[:97] + "..."
                        value += f"Description: {desc}\n"
                    
                    embed.add_field(
                        name=group['name'],
                        value=value,
                        inline=True
                    )
                
                # Create buttons for actions
                components = []
                row = []
                
                for i, group in enumerate(groups[:10]):  # Limit to 10 groups
                    # Create a new row every 3 buttons
                    if i > 0 and i % 3 == 0:
                        components.append(ActionRow(*row))
                        row = []
                    
                    # Add button for this group
                    row.append(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label=group["name"][:20],  # Limit button text
                            custom_id=f"view_group:{group['id']}"
                        )
                    )
                
                # Add final row if there are buttons left
                if row:
                    components.append(ActionRow(*row))
                
                # Add create group button
                components.append(
                    ActionRow(
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="Create New Group",
                            custom_id="create_new_group"
                        )
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error listing groups: {e}")
            return await ctx.send(f"An error occurred while retrieving groups. Please try again later.")
    
    @group_command.subcommand(
        sub_cmd_name="view",
        sub_cmd_description="View a character group's details",
    )
    @slash_option(
        name="group_name",
        description="Name of the group to view",
        required=True,
        opt_type=OptionType.STRING
    )
    async def group_view(self, ctx: SlashContext, group_name: str):
        """View details of a character group."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.description, g.color, g.created_by
                    FROM groups g
                    WHERE g.guild_id = $1 AND g.name ILIKE $2
                """
                result = await session.execute(query, str(ctx.guild_id), group_name)
                group = await result.fetchone()
                
                if not group:
                    return await ctx.send(f"Group '{group_name}' not found.")
                
                # Get group members
                query = """
                    SELECT c.id, c.name, c.server, c.lodestone_id, c.active_class_job,
                           c.discord_user_id
                    FROM characters c
                    JOIN character_group cg ON c.id = cg.character_id
                    WHERE cg.group_id = $1
                    ORDER BY c.name ASC
                """
                result = await session.execute(query, group['id'])
                characters = await result.fetchall()
                
                # Create embed response
                embed_color = int(group['color'][1:], 16) if group['color'] else 0x3498db
                embed = Embed(
                    title=f"Group: {group['name']}",
                    description=group['description'] if group['description'] else "No description",
                    color=embed_color
                )
                
                # Add creator info
                creator = f"<@{group['created_by']}>"
                embed.add_field(name="Created By", value=creator, inline=True)
                
                # Add member count
                embed.add_field(name="Members", value=str(len(characters)), inline=True)
                
                # List members
                if characters:
                    member_list = ""
                    for i, char in enumerate(characters):
                        if i < 10:  # Limit to 10 characters in initial view
                            discord_user = f"<@{char['discord_user_id']}>"
                            member_list += f"• **{char['name']}** ({char['server']}) - {char['active_class_job']} - {discord_user}\n"
                    
                    if len(characters) > 10:
                        member_list += f"*...and {len(characters) - 10} more characters*"
                    
                    embed.add_field(name="Characters", value=member_list, inline=False)
                else:
                    embed.add_field(name="Characters", value="No characters in this group yet.", inline=False)
                
                # Add buttons for actions
                components = [
                    ActionRow(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="Add Characters",
                            custom_id=f"add_characters_to_group:{group['id']}"
                        ),
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="View All Members",
                            custom_id=f"view_all_group_members:{group['id']}"
                        )
                    ),
                    ActionRow(
                        Button(
                            style=ButtonStyle.SECONDARY,
                            label="Edit Group",
                            custom_id=f"edit_group:{group['id']}"
                        ),
                        Button(
                            style=ButtonStyle.DANGER,
                            label="Delete Group",
                            custom_id=f"delete_group:{group['id']}"
                        )
                    )
                ]
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error viewing group: {e}")
            return await ctx.send(f"An error occurred while retrieving the group. Please try again later.")
    
    @component_callback("view_group")
    async def view_group_callback(self, ctx: ComponentContext):
        """Handle group selection from list."""
        # Get group ID from button custom ID
        group_id = ctx.custom_id.split(":")[1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.description, g.color, g.created_by
                    FROM groups g
                    WHERE g.id = $1 AND g.guild_id = $2
                """
                result = await session.execute(query, uuid.UUID(group_id), str(ctx.guild_id))
                group = await result.fetchone()
                
                if not group:
                    return await ctx.edit_origin(
                        content="Group not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Get group members
                query = """
                    SELECT c.id, c.name, c.server, c.lodestone_id, c.active_class_job,
                           c.discord_user_id
                    FROM characters c
                    JOIN character_group cg ON c.id = cg.character_id
                    WHERE cg.group_id = $1
                    ORDER BY c.name ASC
                """
                result = await session.execute(query, group['id'])
                characters = await result.fetchall()
                
                # Create embed response
                embed_color = int(group['color'][1:], 16) if group['color'] else 0x3498db
                embed = Embed(
                    title=f"Group: {group['name']}",
                    description=group['description'] if group['description'] else "No description",
                    color=embed_color
                )
                
                # Add creator info
                creator = f"<@{group['created_by']}>"
                embed.add_field(name="Created By", value=creator, inline=True)
                
                # Add member count
                embed.add_field(name="Members", value=str(len(characters)), inline=True)
                
                # List members
                if characters:
                    member_list = ""
                    for i, char in enumerate(characters):
                        if i < 10:  # Limit to 10 characters in initial view
                            discord_user = f"<@{char['discord_user_id']}>"
                            member_list += f"• **{char['name']}** ({char['server']}) - {char['active_class_job']} - {discord_user}\n"
                    
                    if len(characters) > 10:
                        member_list += f"*...and {len(characters) - 10} more characters*"
                    
                    embed.add_field(name="Characters", value=member_list, inline=False)
                else:
                    embed.add_field(name="Characters", value="No characters in this group yet.", inline=False)
                
                # Add buttons for actions
                components = [
                    ActionRow(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="Add Characters",
                            custom_id=f"add_characters_to_group:{group['id']}"
                        ),
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="View All Members",
                            custom_id=f"view_all_group_members:{group['id']}"
                        )
                    ),
                    ActionRow(
                        Button(
                            style=ButtonStyle.SECONDARY,
                            label="Edit Group",
                            custom_id=f"edit_group:{group['id']}"
                        ),
                        Button(
                            style=ButtonStyle.DANGER,
                            label="Delete Group",
                            custom_id=f"delete_group:{group['id']}"
                        )
                    )
                ]
                
                return await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error viewing group: {e}")
            return await ctx.edit_origin(
                content="An error occurred while retrieving the group. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @component_callback("add_characters_to_group")
    async def add_characters_to_group_callback(self, ctx: ComponentContext):
        """Handle adding characters to a group."""
        # Get group ID from button custom ID
        group_id = ctx.custom_id.split(":")[1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.description, g.color, g.created_by
                    FROM groups g
                    WHERE g.id = $1 AND g.guild_id = $2
                """
                result = await session.execute(query, uuid.UUID(group_id), str(ctx.guild_id))
                group = await result.fetchone()
                
                if not group:
                    return await ctx.edit_origin(
                        content="Group not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Get the user's characters
                query = """
                    SELECT c.id, c.name, c.server, c.lodestone_id, c.active_class_job
                    FROM characters c
                    WHERE c.discord_user_id = $1
                    ORDER BY c.name ASC
                """
                result = await session.execute(query, str(ctx.author.id))
                characters = await result.fetchall()
                
                if not characters:
                    return await ctx.edit_origin(
                        content="You don't have any registered characters. Use `/character register` to add your characters first.",
                        embeds=[],
                        components=[]
                    )
                
                # Get characters already in the group
                query = """
                    SELECT character_id
                    FROM character_group
                    WHERE group_id = $1
                """
                result = await session.execute(query, group['id'])
                existing_characters = [row[0] for row in await result.fetchall()]
                
                # Filter out characters already in the group
                available_characters = [c for c in characters if c['id'] not in existing_characters]
                
                if not available_characters:
                    return await ctx.edit_origin(
                        content="All your characters are already in this group.",
                        embeds=[],
                        components=[]
                    )
                
                # Create embed response
                embed_color = int(group['color'][1:], 16) if group['color'] else 0x3498db
                embed = Embed(
                    title=f"Add Characters to {group['name']}",
                    description="Select characters to add to this group:",
                    color=embed_color
                )
                
                # List available characters
                character_list = ""
                for i, char in enumerate(available_characters):
                    character_list += f"{i+1}. **{char['name']}** ({char['server']}) - {char['active_class_job']}\n"
                
                embed.add_field(name="Your Characters", value=character_list, inline=False)
                
                # Create buttons for each character
                components = []
                row = []
                
                for i, char in enumerate(available_characters[:10]):  # Limit to 10 characters
                    # Create a new row every 3 buttons
                    if i > 0 and i % 3 == 0:
                        components.append(ActionRow(*row))
                        row = []
                    
                    # Add button for this character
                    row.append(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label=char["name"][:20],  # Limit button text
                            custom_id=f"add_character_to_group:{group['id']}:{char['id']}"
                        )
                    )
                
                # Add final row if there are buttons left
                if row:
                    components.append(ActionRow(*row))
                
                # Add cancel button
                components.append(
                    ActionRow(
                        Button(
                            style=ButtonStyle.SECONDARY,
                            label="Cancel",
                            custom_id=f"cancel_add_to_group:{group['id']}"
                        )
                    )
                )
                
                return await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error preparing to add characters: {e}")
            return await ctx.edit_origin(
                content="An error occurred while retrieving characters. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @component_callback("add_character_to_group")
    async def add_character_to_group_final_callback(self, ctx: ComponentContext):
        """Handle final step of adding a character to a group."""
        # Get IDs from button custom ID
        parts = ctx.custom_id.split(":")
        group_id = parts[1]
        character_id = parts[2]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name
                    FROM groups g
                    WHERE g.id = $1 AND g.guild_id = $2
                """
                result = await session.execute(query, uuid.UUID(group_id), str(ctx.guild_id))
                group = await result.fetchone()
                
                if not group:
                    return await ctx.edit_origin(
                        content="Group not found or deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Find the character
                query = """
                    SELECT id, name, server
                    FROM characters
                    WHERE id = $1 AND discord_user_id = $2
                """
                result = await session.execute(query, uuid.UUID(character_id), str(ctx.author.id))
                character = await result.fetchone()
                
                if not character:
                    return await ctx.edit_origin(
                        content="Character not found or not owned by you.",
                        embeds=[],
                        components=[]
                    )
                
                # Add character to group
                query = """
                    INSERT INTO character_group (character_id, group_id)
                    VALUES ($1, $2)
                    ON CONFLICT (character_id, group_id) DO NOTHING
                    RETURNING character_id
                """
                result = await session.execute(query, character['id'], group['id'])
                inserted = await result.fetchone()
                
                if not inserted:
                    return await ctx.edit_origin(
                        content=f"Character {character['name']} is already in the group {group['name']}.",
                        embeds=[],
                        components=[]
                    )
                
                # Success message
                embed = Embed(
                    title="Character Added to Group",
                    description=f"Successfully added **{character['name']}** ({character['server']}) to the group **{group['name']}**.",
                    color=0x2ecc71
                )
                
                # Provide buttons for next steps
                components = [
                    ActionRow(
                        Button(
                            style=ButtonStyle.PRIMARY,
                            label="Add Another Character",
                            custom_id=f"add_characters_to_group:{group['id']}"
                        ),
                        Button(
                            style=ButtonStyle.SUCCESS,
                            label="View Group",
                            custom_id=f"view_group:{group['id']}"
                        )
                    )
                ]
                
                return await ctx.edit_origin(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error adding character to group: {e}")
            return await ctx.edit_origin(
                content="An error occurred while adding the character to the group. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @group_command.subcommand(
        sub_cmd_name="recommend",
        sub_cmd_description="Get farming recommendations for a group",
    )
    @slash_option(
        name="group_name",
        description="Name of the group to get recommendations for",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="type",
        description="Type of recommendation",
        required=False,
        opt_type=OptionType.STRING,
        choices=[
            {"name": "Mounts", "value": "mounts"},
            {"name": "Minions", "value": "minions"},
            {"name": "Both", "value": "both"}
        ]
    )
    async def group_recommend(self, ctx: SlashContext, group_name: str, type: str = "both"):
        """Get farming recommendations for a group."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.description, g.color
                    FROM groups g
                    WHERE g.guild_id = $1 AND g.name ILIKE $2
                """
                result = await session.execute(query, str(ctx.guild_id), group_name)
                group = await result.fetchone()
                
                if not group:
                    return await ctx.send(f"Group '{group_name}' not found.")
                
                # Get all characters in the group
                query = """
                    SELECT c.lodestone_id, c.name, c.server
                    FROM characters c
                    JOIN character_group cg ON c.id = cg.character_id
                    WHERE cg.group_id = $1
                """
                result = await session.execute(query, group['id'])
                characters = await result.fetchall()
                
                if not characters:
                    return await ctx.send(f"No characters found in the group '{group_name}'. Add characters first before getting recommendations.")
                
                # Get progress message
                progress_embed = Embed(
                    title=f"Getting Recommendations for {group_name}",
                    description=f"Analyzing {len(characters)} characters...",
                    color=int(group['color'][1:], 16) if group['color'] else 0x3498db
                )
                progress_message = await ctx.send(embed=progress_embed)
                
                # Get recommendations from engine
                character_ids = [char['lodestone_id'] for char in characters]
                recommendations = await self.recommendation_engine.get_group_recommendations(character_ids)
                
                # Format recommendations
                embed_color = int(group['color'][1:], 16) if group['color'] else 0x3498db
                embed = Embed(
                    title=f"Farming Recommendations for {group_name}",
                    description=f"Based on {len(recommendations['processed_characters'])}/{len(characters)} characters in the group.",
                    color=embed_color
                )
                
                # Show mount recommendations if requested
                if type in ["mounts", "both"] and recommendations['mount_recommendations']:
                    mount_recs = recommendations['mount_recommendations']
                    mount_text = ""
                    
                    for i, rec in enumerate(mount_recs[:5]):
                        mount = rec['mount']
                        missing_count = len(rec['characters'])
                        total_count = len(recommendations['processed_characters'])
                        percent_missing = (missing_count / total_count) * 100
                        
                        # Find the most accessible source
                        best_source = "Unknown"
                        for source in mount.get('sources', []):
                            if source.get('type') in ["Dungeon", "Trial", "Raid"]:
                                source_type = source.get('type')
                                text = source.get('text', '')
                                if 'related_duty' in source and source['related_duty']:
                                    duty_name = source['related_duty'].get('name', '')
                                    best_source = f"{source_type}: {duty_name}"
                                    break
                                else:
                                    best_source = f"{source_type}: {text}"
                                    break
                        
                        mount_text += f"**{i+1}. {mount['name']}** ({missing_count}/{total_count} need, {percent_missing:.1f}%)\n"
                        mount_text += f"Source: {best_source}\n\n"
                    
                    embed.add_field(name="Mount Recommendations", value=mount_text if mount_text else "No mount recommendations available.", inline=False)
                
                # Show minion recommendations if requested
                if type in ["minions", "both"] and recommendations['minion_recommendations']:
                    minion_recs = recommendations['minion_recommendations']
                    minion_text = ""
                    
                    for i, rec in enumerate(minion_recs[:5]):
                        minion = rec['minion']
                        missing_count = len(rec['characters'])
                        total_count = len(recommendations['processed_characters'])
                        percent_missing = (missing_count / total_count) * 100
                        
                        # Find the most accessible source
                        best_source = "Unknown"
                        for source in minion.get('sources', []):
                            if source.get('type') in ["Dungeon", "Trial", "Raid"]:
                                source_type = source.get('type')
                                text = source.get('text', '')
                                if 'related_duty' in source and source['related_duty']:
                                    duty_name = source['related_duty'].get('name', '')
                                    best_source = f"{source_type}: {duty_name}"
                                    break
                                else:
                                    best_source = f"{source_type}: {text}"
                                    break
                        
                        minion_text += f"**{i+1}. {minion['name']}** ({missing_count}/{total_count} need, {percent_missing:.1f}%)\n"
                        minion_text += f"Source: {best_source}\n\n"
                    
                    embed.add_field(name="Minion Recommendations", value=minion_text if minion_text else "No minion recommendations available.", inline=False)
                
                # Add footer
                if len(recommendations['processed_characters']) < len(characters):
                    embed.set_footer(text=f"Note: {len(characters) - len(recommendations['processed_characters'])} characters couldn't be processed. Make sure they have valid Lodestone IDs.")
                
                # Add buttons for actions
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="View Group Details",
                        custom_id=f"view_group:{group['id']}"
                    ),
                    Button(
                        style=ButtonStyle.SUCCESS,
                        label="Detailed Recommendations",
                        custom_id=f"detailed_recommendations:{group['id']}:{type}"
                    )
                )
                
                # Update the message
                await progress_message.edit(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return await ctx.send(f"An error occurred while getting recommendations. Please try again later.")
    
    @group_command.subcommand(
        sub_cmd_name="remove_character",
        sub_cmd_description="Remove a character from a group",
    )
    @slash_option(
        name="group_name",
        description="Group name",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="character_name",
        description="Character name",
        required=True,
        opt_type=OptionType.STRING
    )
    async def group_remove_character(self, ctx: SlashContext, group_name: str, character_name: str):
        """Remove a character from a group."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.created_by
                    FROM groups g
                    WHERE g.guild_id = $1 AND g.name ILIKE $2
                """
                result = await session.execute(query, str(ctx.guild_id), group_name)
                group = await result.fetchone()
                
                if not group:
                    return await ctx.send(f"Group '{group_name}' not found.")
                
                # Check if user has permission to modify this group
                if group['created_by'] != str(ctx.author.id):
                    # For simplicity, only allow the creator to modify
                    # In a real implementation, you'd check manager roles
                    return await ctx.send("You don't have permission to modify this group.")
                
                # Find the character in the group
                query = """
                    SELECT c.id, c.name, c.server, c.discord_user_id, cg.character_id
                    FROM characters c
                    JOIN character_group cg ON c.id = cg.character_id
                    WHERE cg.group_id = $1 AND c.name ILIKE $2
                """
                result = await session.execute(query, group['id'], character_name)
                character = await result.fetchone()
                
                if not character:
                    return await ctx.send(f"Character '{character_name}' not found in group '{group_name}'.")
                
                # Remove character from group
                query = """
                    DELETE FROM character_group
                    WHERE group_id = $1 AND character_id = $2
                    RETURNING character_id
                """
                result = await session.execute(query, group['id'], character['id'])
                deleted = await result.fetchone()
                
                if not deleted:
                    return await ctx.send(f"Failed to remove character from group. Please try again later.")
                
                # Success message
                embed = Embed(
                    title="Character Removed from Group",
                    description=f"Successfully removed **{character['name']}** ({character['server']}) from the group **{group['name']}**.",
                    color=0x2ecc71
                )
                
                # Mention character owner
                if character['discord_user_id']:
                    embed.add_field(name="Character Owner", value=f"<@{character['discord_user_id']}>", inline=True)
                
                # Add buttons for next steps
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="View Group",
                        custom_id=f"view_group:{group['id']}"
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
                
        except Exception as e:
            logger.error(f"Error removing character from group: {e}")
            return await ctx.send(f"An error occurred while removing the character from the group. Please try again later.")
    
    @group_command.subcommand(
        sub_cmd_name="delete",
        sub_cmd_description="Delete a character group",
    )
    @slash_option(
        name="group_name",
        description="Group name",
        required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="confirm",
        description="Type 'confirm' to delete the group",
        required=True,
        opt_type=OptionType.STRING
    )
    async def group_delete(self, ctx: SlashContext, group_name: str, confirm: str):
        """Delete a character group."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Check confirmation
            if confirm.lower() != "confirm":
                return await ctx.send("Group deletion cancelled. To delete a group, please type 'confirm' in the confirm field.")
            
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.created_by
                    FROM groups g
                    WHERE g.guild_id = $1 AND g.name ILIKE $2
                """
                result = await session.execute(query, str(ctx.guild_id), group_name)
                group = await result.fetchone()
                
                if not group:
                    return await ctx.send(f"Group '{group_name}' not found.")
                
                # Check if user has permission to delete this group
                if group['created_by'] != str(ctx.author.id):
                    # For simplicity, only allow the creator to delete
                    # In a real implementation, you'd check manager roles
                    return await ctx.send("You don't have permission to delete this group.")
                
                # Delete all character associations first
                query = """
                    DELETE FROM character_group
                    WHERE group_id = $1
                    RETURNING character_id
                """
                result = await session.execute(query, group['id'])
                associations = await result.fetchall()
                
                # Delete the group
                query = """
                    DELETE FROM groups
                    WHERE id = $1
                    RETURNING id
                """
                result = await session.execute(query, group['id'])
                deleted = await result.fetchone()
                
                if not deleted:
                    return await ctx.send(f"Failed to delete group. Please try again later.")
                
                # Success message
                embed = Embed(
                    title="Group Deleted",
                    description=f"Successfully deleted the group **{group['name']}** and removed {len(associations)} character associations.",
                    color=0xe74c3c
                )
                
                return await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return await ctx.send(f"An error occurred while deleting the group. Please try again later.")
    
    @component_callback("create_new_group")
    async def create_new_group_callback(self, ctx: ComponentContext):
        """Handle creating a new group via button."""
        # Create modal for group creation
        modal = Modal(
            title="Create New Group",
            custom_id="create_group_modal",
            components=[
                TextInput(
                    style=TextStyleType.SHORT,
                    label="Group Name",
                    custom_id="group_name",
                    placeholder="Enter a name for your group",
                    min_length=1,
                    max_length=100,
                    required=True
                ),
                TextInput(
                    style=TextStyleType.PARAGRAPH,
                    label="Description",
                    custom_id="group_description",
                    placeholder="Enter a description for your group (optional)",
                    min_length=0,
                    max_length=500,
                    required=False
                ),
                TextInput(
                    style=TextStyleType.SHORT,
                    label="Color (hex code)",
                    custom_id="group_color",
                    placeholder="#3498db (optional)",
                    min_length=0,
                    max_length=7,
                    required=False
                )
            ]
        )
        
        await ctx.popup(modal)
    
    @listen("modal_submit")
    async def on_modal_submit(self, ctx: ModalContext):
        """Handle modal submissions."""
        if ctx.custom_id == "create_group_modal":
            # Get form data
            group_name = ctx.responses.get("group_name", "")
            group_description = ctx.responses.get("group_description", "")
            group_color = ctx.responses.get("group_color", "")
            
            # Trigger the group creation
            await self.group_create(ctx, group_name, group_description, group_color)
    
    @component_callback("delete_group")
    async def delete_group_callback(self, ctx: ComponentContext):
        """Handle group deletion via button."""
        # Get group ID from button custom ID
        group_id = ctx.custom_id.split(":")[1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.created_by
                    FROM groups g
                    WHERE g.id = $1 AND g.guild_id = $2
                """
                result = await session.execute(query, uuid.UUID(group_id), str(ctx.guild_id))
                group = await result.fetchone()
                
                if not group:
                    return await ctx.edit_origin(
                        content="Group not found or already deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Check if user has permission
                if group['created_by'] != str(ctx.author.id):
                    return await ctx.edit_origin(
                        content="You don't have permission to delete this group.",
                        embeds=[],
                        components=[]
                    )
                
                # Ask for confirmation
                confirm_embed = Embed(
                    title="Confirm Group Deletion",
                    description=(
                        f"Are you sure you want to delete the group **{group['name']}**?\n\n"
                        "This action cannot be undone, and all character associations will be removed."
                    ),
                    color=0xe74c3c
                )
                
                components = ActionRow(
                    Button(
                        style=ButtonStyle.DANGER,
                        label="Delete Group",
                        custom_id=f"confirm_delete_group:{group['id']}"
                    ),
                    Button(
                        style=ButtonStyle.SECONDARY,
                        label="Cancel",
                        custom_id=f"cancel_delete_group:{group['id']}"
                    )
                )
                
                return await ctx.edit_origin(embed=confirm_embed, components=[components])
                
        except Exception as e:
            logger.error(f"Error preparing group deletion: {e}")
            return await ctx.edit_origin(
                content="An error occurred while preparing group deletion. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @component_callback("confirm_delete_group")
    async def confirm_delete_group_callback(self, ctx: ComponentContext):
        """Handle final confirmation of group deletion."""
        # Get group ID from button custom ID
        group_id = ctx.custom_id.split(":")[1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            async with get_db_session() as session:
                # Find the group
                query = """
                    SELECT g.id, g.name, g.created_by
                    FROM groups g
                    WHERE g.id = $1 AND g.guild_id = $2
                """
                result = await session.execute(query, uuid.UUID(group_id), str(ctx.guild_id))
                group = await result.fetchone()
                
                if not group:
                    return await ctx.edit_origin(
                        content="Group not found or already deleted.",
                        embeds=[],
                        components=[]
                    )
                
                # Check if user has permission
                if group['created_by'] != str(ctx.author.id):
                    return await ctx.edit_origin(
                        content="You don't have permission to delete this group.",
                        embeds=[],
                        components=[]
                    )
                
                # Delete all character associations first
                query = """
                    DELETE FROM character_group
                    WHERE group_id = $1
                    RETURNING character_id
                """
                result = await session.execute(query, group['id'])
                associations = await result.fetchall()
                
                # Delete the group
                query = """
                    DELETE FROM groups
                    WHERE id = $1
                    RETURNING id
                """
                result = await session.execute(query, group['id'])
                deleted = await result.fetchone()
                
                if not deleted:
                    return await ctx.edit_origin(
                        content="Failed to delete group. Please try again later.",
                        embeds=[],
                        components=[]
                    )
                
                # Success message
                deleted_embed = Embed(
                    title="Group Deleted",
                    description=f"Successfully deleted the group **{group['name']}** and removed {len(associations)} character associations.",
                    color=0xe74c3c
                )
                
                # Add button to view other groups
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="View All Groups",
                        custom_id="list_all_groups"
                    )
                )
                
                return await ctx.edit_origin(embed=deleted_embed, components=[components])
                
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return await ctx.edit_origin(
                content="An error occurred while deleting the group. Please try again later.",
                embeds=[],
                components=[]
            )
    
    @component_callback("cancel_delete_group")
    async def cancel_delete_group_callback(self, ctx: ComponentContext):
        """Handle cancellation of group deletion."""
        # Get group ID from button custom ID
        group_id = ctx.custom_id.split(":")[1]
        
        # Navigate back to group view
        await ctx.defer(edit_origin=True)
        await self.view_group_callback(ctx)
    
    @component_callback("list_all_groups")
    async def list_all_groups_callback(self, ctx: ComponentContext):
        """Handle listing all groups button press."""
        # Trigger the group list command
        await ctx.defer(edit_origin=True)
        
        # Create a new SlashContext-like object to trigger the list command
        # In a real implementation, you'd carefully handle this to avoid duplicating code
        # For simplicity, we'll just call the method directly
        await self.group_list(ctx)

# Setup function to register the extension
async def setup(client: Client) -> Extension:
    """
    Setup function for the Groups extension.
    
    Args:
        client: The Discord bot client
    
    Returns:
        An instance of the Groups extension
    """
    class _GroupsCog(GroupsCog):
        """
        Subclass with a unique name to avoid extension conflicts
        """
        name = "FFXIVGroupsCog"
    
    return _GroupsCog(client)