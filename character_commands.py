"""
Character management commands for the FFXIV Discord bot.
"""
import logging
from typing import Optional

from interactions import (
    Extension,
    Client,
    SlashContext,
    slash_command,
    slash_option,
    OptionType,
    Embed,
    ButtonStyle,
    Button,
    ActionRow,
    ComponentContext,
    component_callback
)

import database as db

# Set up logger
logger = logging.getLogger("ffxiv_bot")

class CharacterCommandsCog(Extension):
    """Character management commands."""
    
    def __init__(self, client: Client):
        self.client = client
    
    @slash_command(
        name="character",
        description="Character management commands",
    )
    async def character_command(self, ctx: SlashContext):
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
    @slash_option(
        name="primary",
        description="Set as primary character?",
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
        """Register a new character."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Check if character already exists
            existing_char = db.get_character_by_name_server(name, server)
            if existing_char and existing_char['discord_user_id'] == str(ctx.author.id):
                # Character already registered by this user
                embed = Embed(
                    title="Character Already Registered",
                    description=f"You've already registered {name} on {server}",
                    color=0xe74c3c
                )
                
                # Add button to view characters
                components = ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="View Your Characters",
                        custom_id="view_characters"
                    )
                )
                
                return await ctx.send(embed=embed, components=components)
            
            # If no primary is specified, make this the primary if the user has no characters
            if not primary:
                user_characters = db.get_user_characters(str(ctx.author.id))
                if not user_characters:
                    primary = True
            
            # Add the character to the database
            character_id = db.add_character(
                discord_user_id=str(ctx.author.id),
                name=name,
                server=server,
                is_primary=primary
            )
            
            logger.info(f"Registered character {name} on {server} for user {ctx.author.id}")
            
            # Create embed response
            embed = Embed(
                title="Character Registered",
                description=f"Successfully registered {name} on {server}",
                color=0x3498db
            )
            
            embed.add_field(name="Character Name", value=name, inline=True)
            embed.add_field(name="Server", value=server, inline=True)
            embed.add_field(name="Primary Character", value="Yes" if primary else "No", inline=True)
            embed.add_field(name="Owner", value=ctx.author.mention, inline=True)
            
            # Add buttons for next steps
            components = ActionRow(
                Button(
                    style=ButtonStyle.PRIMARY,
                    label="Verify Character",
                    custom_id=f"verify_character:{character_id}"
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="View Your Characters",
                    custom_id="view_characters"
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
    async def character_list(self, ctx: SlashContext):
        """List registered characters."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Get user's characters from database
            characters = db.get_user_characters(str(ctx.author.id))
            
            if not characters:
                embed = Embed(
                    title="No Characters Found",
                    description="You don't have any registered characters. Use `/character register` to add one.",
                    color=0xe74c3c
                )
                
                return await ctx.send(embed=embed)
            
            # Create embed response
            embed = Embed(
                title="Your FFXIV Characters",
                description=f"You have {len(characters)} registered character(s)",
                color=0x3498db
            )
            
            # Add each character to the embed
            for char in characters:
                # Format character information
                status = []
                if char['is_primary']:
                    status.append("✅ Primary")
                if char['verified']:
                    status.append("✓ Verified")
                else:
                    status.append("❌ Not Verified")
                
                # Add job info if available
                job_info = ""
                if char['active_job'] and char['job_level']:
                    job_info = f"\nLevel {char['job_level']} {char['active_job']}"
                
                value = f"Server: {char['server']}\nStatus: {', '.join(status)}{job_info}"
                
                embed.add_field(
                    name=char['name'],
                    value=value,
                    inline=True
                )
            
            # Add buttons for actions
            components = []
            
            # Create character action buttons
            if len(characters) > 0:
                primary_buttons = []
                for i, char in enumerate(characters[:3]):  # Limit to first 3
                    btn_style = ButtonStyle.SUCCESS if char['is_primary'] else ButtonStyle.SECONDARY
                    btn_label = f"Set {char['name']} as Primary" if not char['is_primary'] else f"{char['name']} (Primary)"
                    
                    primary_buttons.append(
                        Button(
                            style=btn_style,
                            label=btn_label[:25],  # Limit button text length
                            custom_id=f"set_primary:{char['id']}"
                        )
                    )
                
                if primary_buttons:
                    components.append(ActionRow(*primary_buttons))
            
            # Add register button
            components.append(
                ActionRow(
                    Button(
                        style=ButtonStyle.PRIMARY,
                        label="Register New Character",
                        custom_id="register_character_modal"
                    ),
                    Button(
                        style=ButtonStyle.DANGER,
                        label="Remove Character",
                        custom_id="remove_character_select"
                    )
                )
            )
            
            await ctx.send(embed=embed, components=components)
            
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            await ctx.send("An error occurred while retrieving your characters. Please try again later.")
    
    @character_command.subcommand(
        sub_cmd_name="remove",
        sub_cmd_description="Remove a character",
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
    async def character_remove(self, ctx: SlashContext, name: str, server: str):
        """Remove a character."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Find the character
            character = db.get_character_by_name_server(name, server)
            
            if not character:
                embed = Embed(
                    title="Character Not Found",
                    description=f"No character named {name} on {server} was found in your registered characters.",
                    color=0xe74c3c
                )
                
                return await ctx.send(embed=embed)
            
            # Check ownership
            if character['discord_user_id'] != str(ctx.author.id):
                embed = Embed(
                    title="Permission Denied",
                    description="You can only remove characters that you own.",
                    color=0xe74c3c
                )
                
                return await ctx.send(embed=embed)
            
            # Create confirmation embed
            embed = Embed(
                title="Confirm Character Removal",
                description=f"Are you sure you want to remove {name} ({server}) from your registered characters?",
                color=0xe74c3c
            )
            
            # Add buttons for confirmation
            components = ActionRow(
                Button(
                    style=ButtonStyle.DANGER,
                    label="Remove Character",
                    custom_id=f"confirm_remove:{character['id']}"
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="Cancel",
                    custom_id="cancel_remove"
                )
            )
            
            await ctx.send(embed=embed, components=components)
            
        except Exception as e:
            logger.error(f"Error preparing character removal: {e}")
            await ctx.send("An error occurred while processing your request. Please try again later.")
    
    @character_command.subcommand(
        sub_cmd_name="set_primary",
        sub_cmd_description="Set a character as your primary character",
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
    async def character_set_primary(self, ctx: SlashContext, name: str, server: str):
        """Set a character as primary."""
        # Defer response while we process
        await ctx.defer()
        
        try:
            # Find the character
            character = db.get_character_by_name_server(name, server)
            
            if not character:
                embed = Embed(
                    title="Character Not Found",
                    description=f"No character named {name} on {server} was found in your registered characters.",
                    color=0xe74c3c
                )
                
                return await ctx.send(embed=embed)
            
            # Check ownership
            if character['discord_user_id'] != str(ctx.author.id):
                embed = Embed(
                    title="Permission Denied",
                    description="You can only set your own characters as primary.",
                    color=0xe74c3c
                )
                
                return await ctx.send(embed=embed)
            
            # Set as primary
            success = db.set_primary_character(character['id'], str(ctx.author.id))
            
            if success:
                embed = Embed(
                    title="Primary Character Updated",
                    description=f"{name} ({server}) is now your primary character.",
                    color=0x3498db
                )
                
                # Add button to view characters
                components = ActionRow(
                    Button(
                        style=ButtonStyle.SECONDARY,
                        label="View Your Characters",
                        custom_id="view_characters"
                    )
                )
                
                await ctx.send(embed=embed, components=components)
            else:
                await ctx.send("An error occurred while updating your primary character. Please try again later.")
            
        except Exception as e:
            logger.error(f"Error setting primary character: {e}")
            await ctx.send("An error occurred while processing your request. Please try again later.")
    
    @component_callback("view_characters")
    async def view_characters_callback(self, ctx: ComponentContext):
        """Handle the View Characters button."""
        # Call the character_list command
        await self.character_list(ctx)
    
    @component_callback("register_character_modal")
    async def register_character_modal_callback(self, ctx: ComponentContext):
        """Handle the Register Character button."""
        await ctx.send("To register a character, use the `/character register` command with your character name and server.")
    
    @component_callback("confirm_remove")
    async def confirm_remove_callback(self, ctx: ComponentContext):
        """Handle character removal confirmation."""
        # Extract character ID from custom ID
        character_id = int(ctx.custom_id.split(":")[-1])
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            # Get character info for the message
            character = db.get_character(character_id)
            
            if not character:
                embed = Embed(
                    title="Character Not Found",
                    description="The character you're trying to remove was not found.",
                    color=0xe74c3c
                )
                
                return await ctx.edit_origin(embed=embed, components=[])
            
            # Remove the character
            success = db.remove_character(character_id, str(ctx.author.id))
            
            if success:
                embed = Embed(
                    title="Character Removed",
                    description=f"{character['name']} ({character['server']}) has been removed from your registered characters.",
                    color=0x3498db
                )
                
                # Add button to view remaining characters
                components = ActionRow(
                    Button(
                        style=ButtonStyle.SECONDARY,
                        label="View Your Characters",
                        custom_id="view_characters"
                    )
                )
                
                await ctx.edit_origin(embed=embed, components=components)
            else:
                embed = Embed(
                    title="Error",
                    description="An error occurred while removing the character. Please try again later.",
                    color=0xe74c3c
                )
                
                await ctx.edit_origin(embed=embed, components=[])
            
        except Exception as e:
            logger.error(f"Error removing character: {e}")
            embed = Embed(
                title="Error",
                description="An error occurred while processing your request. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.edit_origin(embed=embed, components=[])
    
    @component_callback("cancel_remove")
    async def cancel_remove_callback(self, ctx: ComponentContext):
        """Handle cancellation of character removal."""
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        # Just call the character list to show their characters instead
        await self.character_list(ctx)
    
    @component_callback("set_primary")
    async def set_primary_callback(self, ctx: ComponentContext):
        """Handle setting a character as primary."""
        # Extract character ID from custom ID
        character_id = int(ctx.custom_id.split(":")[-1])
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            # Get character info for the message
            character = db.get_character(character_id)
            
            if not character:
                embed = Embed(
                    title="Character Not Found",
                    description="The character you're trying to set as primary was not found.",
                    color=0xe74c3c
                )
                
                return await ctx.edit_origin(embed=embed, components=[])
            
            # Set as primary
            success = db.set_primary_character(character_id, str(ctx.author.id))
            
            if success:
                embed = Embed(
                    title="Primary Character Updated",
                    description=f"{character['name']} ({character['server']}) is now your primary character.",
                    color=0x3498db
                )
                
                # Show updated character list
                await self.character_list(ctx)
            else:
                embed = Embed(
                    title="Error",
                    description="An error occurred while updating your primary character. Please try again later.",
                    color=0xe74c3c
                )
                
                await ctx.edit_origin(embed=embed, components=[])
            
        except Exception as e:
            logger.error(f"Error setting primary character: {e}")
            embed = Embed(
                title="Error",
                description="An error occurred while processing your request. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.edit_origin(embed=embed, components=[])
    
    @component_callback("verify_character")
    async def verify_character_callback(self, ctx: ComponentContext):
        """Handle character verification."""
        # Extract character ID from custom ID
        character_id = int(ctx.custom_id.split(":")[-1])
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            # Get character info for the message
            character = db.get_character(character_id)
            
            if not character:
                embed = Embed(
                    title="Character Not Found",
                    description="The character you're trying to verify was not found.",
                    color=0xe74c3c
                )
                
                return await ctx.edit_origin(embed=embed, components=[])
            
            # In a full implementation, this would connect to XIVAPI for verification
            # For now, just show instructions
            embed = Embed(
                title="Character Verification",
                description=f"To verify {character['name']} ({character['server']}) as your character:",
                color=0x3498db
            )
            
            embed.add_field(
                name="Verification Process",
                value=(
                    "1. Log into the game with this character\n"
                    "2. Update your Lodestone profile\n"
                    "3. Add the following text to your character profile: `VERIFY" + f":{ctx.author.id}" + "`\n"
                    "4. Wait for the Lodestone to update (can take 15+ minutes)\n"
                    "5. Click the button below to complete verification"
                ),
                inline=False
            )
            
            # In a real implementation, we'd store the verification code in the database
            
            # Add verification button
            components = ActionRow(
                Button(
                    style=ButtonStyle.SUCCESS,
                    label="Complete Verification",
                    custom_id=f"complete_verification:{character_id}"
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="Cancel",
                    custom_id="view_characters"
                )
            )
            
            await ctx.edit_origin(embed=embed, components=components)
            
        except Exception as e:
            logger.error(f"Error preparing character verification: {e}")
            embed = Embed(
                title="Error",
                description="An error occurred while processing your request. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.edit_origin(embed=embed, components=[])
    
    @component_callback("complete_verification")
    async def complete_verification_callback(self, ctx: ComponentContext):
        """Handle completion of character verification."""
        # Extract character ID from custom ID
        character_id = int(ctx.custom_id.split(":")[-1])
        
        # Defer response while we process
        await ctx.defer(edit_origin=True)
        
        try:
            # Get character info for the message
            character = db.get_character(character_id)
            
            if not character:
                embed = Embed(
                    title="Character Not Found",
                    description="The character you're trying to verify was not found.",
                    color=0xe74c3c
                )
                
                return await ctx.edit_origin(embed=embed, components=[])
            
            # In a real implementation, this would check the Lodestone profile
            # For now, just simulate successful verification
            success = db.mark_character_verified(character_id)
            
            if success:
                embed = Embed(
                    title="Character Verified",
                    description=f"{character['name']} ({character['server']}) has been verified as your character!",
                    color=0x2ecc71
                )
                
                # Add button to view characters
                components = ActionRow(
                    Button(
                        style=ButtonStyle.SECONDARY,
                        label="View Your Characters",
                        custom_id="view_characters"
                    )
                )
                
                await ctx.edit_origin(embed=embed, components=components)
            else:
                embed = Embed(
                    title="Verification Failed",
                    description="An error occurred during verification. Please try again later.",
                    color=0xe74c3c
                )
                
                await ctx.edit_origin(embed=embed, components=[])
            
        except Exception as e:
            logger.error(f"Error verifying character: {e}")
            embed = Embed(
                title="Error",
                description="An error occurred while processing your request. Please try again later.",
                color=0xe74c3c
            )
            
            await ctx.edit_origin(embed=embed, components=[])