"""
Character lookup commands for the FFXIV Discord bot.
"""
import logging
from typing import Optional, Dict, Any, List

from interactions import (
    Extension,
    Client,
    SlashContext,
    slash_command,
    slash_option,
    OptionType,
    Embed,
    EmbedField,
    EmbedFooter,
    ButtonStyle,
    Button,
    ActionRow,
    ComponentContext,
    component_callback
)

from xivapi import XIVAPIClient

# Set up logger
logger = logging.getLogger("ffxiv_bot")

class CharacterLookupCog(Extension):
    """Character lookup commands."""
    
    def __init__(self, client: Client):
        self.client = client
        self.xivapi = XIVAPIClient()
        
        # Cache data centers and servers
        self.data_centers = {}
        self.servers = []
    
    async def initialize(self):
        """Initialize API client and cache data."""
        await self.xivapi.initialize()
        
        # Cache data centers and servers
        self.data_centers = await self.xivapi.get_data_centers()
        self.servers = await self.xivapi.get_servers()
        
        logger.info(f"Cached {len(self.servers)} servers in {len(self.data_centers)} data centers")
    
    @slash_command(
        name="lookup",
        description="Look up a character on the Lodestone",
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
        required=False,
        opt_type=OptionType.STRING
    )
    async def lookup_character(self, ctx: SlashContext, name: str, server: Optional[str] = None):
        """Look up a character on the Lodestone."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Initialize API if needed
            if not self.servers:
                await self.initialize()
            
            # Search for the character
            results = await self.xivapi.search_character(name, server)
            
            # Check for errors
            if "Error" in results:
                embed = Embed(
                    title="API Error",
                    description=f"Error looking up character: {results['Error']}",
                    color=0xe74c3c
                )
                return await ctx.send(embed=embed)
            
            # Check if we have results
            if "Results" not in results or not results["Results"]:
                embed = Embed(
                    title="No Results Found",
                    description=f"No characters found matching '{name}'{f' on {server}' if server else ''}",
                    color=0xe74c3c
                )
                return await ctx.send(embed=embed)
            
            # If there's only one result, show detailed info right away
            if len(results["Results"]) == 1:
                character = results["Results"][0]
                return await self._show_character_details(ctx, character["ID"])
            
            # Multiple results, show a selection screen
            embed = Embed(
                title="Character Search Results",
                description=f"Found {len(results['Results'])} characters matching '{name}'{f' on {server}' if server else ''}",
                color=0x3498db
            )
            
            # Add the first 10 results to the embed
            for i, character in enumerate(results["Results"][:10]):
                embed.add_field(
                    name=f"{i+1}. {character['Name']}",
                    value=f"Server: {character['Server']}\nID: {character['ID']}",
                    inline=True
                )
            
            # Create buttons for selection (up to 5 characters)
            components = []
            buttons = []
            
            for i, character in enumerate(results["Results"][:5]):  # Limit to first 5
                buttons.append(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label=f"{character['Name']} ({character['Server']})"[:25],
                        custom_id=f"view_character:{character['ID']}"
                    )
                )
                
                # Create a new row every 3 buttons
                if (i + 1) % 3 == 0 or i == len(results["Results"][:5]) - 1:
                    components.append(ActionRow(*buttons))
                    buttons = []
            
            await ctx.send(embed=embed, components=components)
            
        except Exception as e:
            logger.error(f"Error looking up character: {e}")
            
            embed = Embed(
                title="Error",
                description="An error occurred while looking up the character. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.send(embed=embed)
    
    async def _show_character_details(self, ctx: SlashContext, lodestone_id: str):
        """
        Show detailed character information.
        
        Args:
            ctx: Command context
            lodestone_id: Character's Lodestone ID
        """
        try:
            # Get detailed character information
            character_data = await self.xivapi.get_character(lodestone_id, extended=True)
            
            # Check for errors
            if "Error" in character_data:
                embed = Embed(
                    title="API Error",
                    description=f"Error fetching character details: {character_data['Error']}",
                    color=0xe74c3c
                )
                return await ctx.send(embed=embed)
            
            # Create basic embed
            embed = Embed(
                title=f"{character_data['Character']['Name']}",
                description=f"Level {character_data['Character']['ActiveClassJob']['Level']} {character_data['Character']['ActiveClassJob']['UnlockedState']['Name']}",
                color=0x3498db
            )
            
            # Set thumbnail to character avatar
            embed.set_thumbnail(url=character_data['Character']['Avatar'])
            
            # Basic info
            basic_info = [
                f"**Server:** {character_data['Character']['Server']} ({character_data['Character']['DC']})",
                f"**Race/Clan:** {character_data['Character']['Race']['Name']} {character_data['Character']['Tribe']['Name']}",
                f"**Gender:** {'♂' if character_data['Character']['Gender'] == 1 else '♀'}"
            ]
            
            # Add title if available
            if character_data['Character'].get('Title'):
                basic_info.append(f"**Title:** {character_data['Character']['Title']['Name']}")
            
            embed.add_field(
                name="Character Info",
                value="\n".join(basic_info),
                inline=False
            )
            
            # Add Free Company if available
            if "FreeCompany" in character_data and character_data["FreeCompany"]:
                fc = character_data["FreeCompany"]
                embed.add_field(
                    name="Free Company",
                    value=f"**{fc['Name']}** «{fc['Tag']}»\n{fc.get('Server', '')}\n{fc.get('Rank', '')} members",
                    inline=True
                )
            
            # Job levels (if available)
            if "ClassJobs" in character_data["Character"]:
                # Group by role
                tanks = []
                healers = []
                dps = []
                crafters = []
                gatherers = []
                
                for job in character_data["Character"]["ClassJobs"]:
                    name = job["UnlockedState"]["Name"]
                    level = job["Level"]
                    
                    if level == 0:
                        continue
                        
                    job_text = f"{name}: {level}"
                    
                    # Sort into role
                    if name in ["Paladin", "Warrior", "Dark Knight", "Gunbreaker"]:
                        tanks.append(job_text)
                    elif name in ["White Mage", "Scholar", "Astrologian", "Sage"]:
                        healers.append(job_text)
                    elif name in ["Alchemist", "Armorer", "Blacksmith", "Carpenter", "Culinarian", "Goldsmith", "Leatherworker", "Weaver"]:
                        crafters.append(job_text)
                    elif name in ["Botanist", "Fisher", "Miner"]:
                        gatherers.append(job_text)
                    else:
                        dps.append(job_text)
                
                # Add fields for each role that has jobs
                if tanks:
                    embed.add_field(name="Tanks", value=", ".join(tanks), inline=True)
                if healers:
                    embed.add_field(name="Healers", value=", ".join(healers), inline=True)
                if dps:
                    embed.add_field(name="DPS", value=", ".join(dps), inline=True)
                
                # Add crafters and gatherers
                if crafters:
                    embed.add_field(name="Crafters", value=", ".join(crafters), inline=True)
                if gatherers:
                    embed.add_field(name="Gatherers", value=", ".join(gatherers), inline=True)
            
            # Add collection counts if available
            if "Minions" in character_data and "Mounts" in character_data:
                embed.add_field(
                    name="Collections",
                    value=f"**Minions:** {len(character_data['Minions'])}\n**Mounts:** {len(character_data['Mounts'])}",
                    inline=True
                )
            
            # Add Lodestone link
            embed.add_field(
                name="Lodestone Link",
                value=f"[View on Lodestone](https://na.finalfantasyxiv.com/lodestone/character/{lodestone_id}/)",
                inline=False
            )
            
            # Set footer with Lodestone ID
            embed.set_footer(text=f"Lodestone ID: {lodestone_id}")
            
            # Add buttons for additional options
            components = ActionRow(
                Button(
                    style=ButtonStyle.LINK,
                    label="Open Lodestone",
                    url=f"https://na.finalfantasyxiv.com/lodestone/character/{lodestone_id}/"
                ),
                Button(
                    style=ButtonStyle.PRIMARY,
                    label="View Collection",
                    custom_id=f"view_collections:{lodestone_id}"
                )
            )
            
            await ctx.send(embed=embed, components=components)
            
        except Exception as e:
            logger.error(f"Error showing character details: {e}")
            
            embed = Embed(
                title="Error",
                description="An error occurred while fetching character details. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.send(embed=embed)
    
    @component_callback("view_character")
    async def view_character_callback(self, ctx: ComponentContext):
        """Handle character selection."""
        # Extract lodestone ID from custom ID
        lodestone_id = ctx.custom_id.split(":")[-1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            await self._show_character_details(ctx, lodestone_id)
        except Exception as e:
            logger.error(f"Error handling character selection: {e}")
            
            embed = Embed(
                title="Error",
                description="An error occurred while fetching character details. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.edit_origin(embed=embed, components=[])
    
    @component_callback("view_collections")
    async def view_collections_callback(self, ctx: ComponentContext):
        """Handle viewing character collections."""
        # Extract lodestone ID from custom ID
        lodestone_id = ctx.custom_id.split(":")[-1]
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            # Get detailed character information
            character_data = await self.xivapi.get_character(lodestone_id, extended=True)
            
            # Check for errors
            if "Error" in character_data:
                embed = Embed(
                    title="API Error",
                    description=f"Error fetching character collections: {character_data['Error']}",
                    color=0xe74c3c
                )
                return await ctx.edit_origin(embed=embed, components=[])
            
            # Create collections embed
            embed = Embed(
                title=f"{character_data['Character']['Name']}'s Collections",
                description=f"Collection information for {character_data['Character']['Name']} from {character_data['Character']['Server']}",
                color=0x3498db
            )
            
            # Set thumbnail to character avatar
            embed.set_thumbnail(url=character_data['Character']['Avatar'])
            
            # Add mount info if available
            if "Mounts" in character_data:
                mount_count = len(character_data["Mounts"])
                
                # Get 5 random mounts to display
                import random
                sample_size = min(5, mount_count)
                sample_mounts = random.sample(character_data["Mounts"], sample_size) if mount_count > 0 else []
                
                mount_text = f"Total Mounts: {mount_count}\n\n"
                if sample_mounts:
                    mount_text += "**Sample Mounts:**\n"
                    mount_text += "\n".join([mount["Name"] for mount in sample_mounts])
                else:
                    mount_text += "No mounts found."
                
                embed.add_field(
                    name="Mounts",
                    value=mount_text,
                    inline=True
                )
            
            # Add minion info if available
            if "Minions" in character_data:
                minion_count = len(character_data["Minions"])
                
                # Get 5 random minions to display
                import random
                sample_size = min(5, minion_count)
                sample_minions = random.sample(character_data["Minions"], sample_size) if minion_count > 0 else []
                
                minion_text = f"Total Minions: {minion_count}\n\n"
                if sample_minions:
                    minion_text += "**Sample Minions:**\n"
                    minion_text += "\n".join([minion["Name"] for minion in sample_minions])
                else:
                    minion_text += "No minions found."
                
                embed.add_field(
                    name="Minions",
                    value=minion_text,
                    inline=True
                )
            
            # Add back button
            components = ActionRow(
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="Back to Character",
                    custom_id=f"view_character:{lodestone_id}"
                ),
                Button(
                    style=ButtonStyle.LINK,
                    label="Open Lodestone",
                    url=f"https://na.finalfantasyxiv.com/lodestone/character/{lodestone_id}/"
                )
            )
            
            await ctx.edit_origin(embed=embed, components=components)
            
        except Exception as e:
            logger.error(f"Error showing collections: {e}")
            
            embed = Embed(
                title="Error",
                description="An error occurred while fetching collections. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.edit_origin(embed=embed, components=[])

# Setup function to register the extension
async def setup(client: Client) -> Extension:
    """Set up the character lookup extension."""
    cog = CharacterLookupCog(client)
    await cog.initialize()
    return cog