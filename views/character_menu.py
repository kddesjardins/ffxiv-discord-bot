"""
Character selection and management menu view.
"""
from typing import List, Optional, Callable, Awaitable

from interactions import (
    ComponentContext,
    Embed,
    SelectMenu,
    SelectOption,
    Button,
    ButtonStyle,
    ActionRow
)

class CharacterMenu:
    """
    Interactive menu for character selection and management.
    """
    def __init__(
        self, 
        characters: List[dict], 
        on_select: Optional[Callable[[str], Awaitable[None]]] = None,
        title: str = "Select a Character",
        description: str = "Choose a character from the list"
    ):
        """
        Initialize the character selection menu.
        
        Args:
            characters: List of character dictionaries
            on_select: Async callback function when a character is selected
            title: Menu title
            description: Menu description
        """
        self.characters = characters
        self.on_select = on_select
        self.title = title
        self.description = description
    
    def create_character_select(self) -> ActionRow:
        """
        Create a select menu with available characters.
        
        Returns:
            ActionRow with character selection menu
        """
        # Prepare select options
        options = []
        for char in self.characters:
            # Format option label and description
            label = f"{char.get('name', 'Unknown')} ({char.get('server', 'Unknown Server')})"
            description = f"Job: {char.get('active_class_job', 'No Job')} | Lodestone ID: {char.get('lodestone_id', 'N/A')}"
            
            options.append(
                SelectOption(
                    label=label,
                    value=str(char.get('id', '')),
                    description=description
                )
            )
        
        # Create select menu
        return ActionRow(
            SelectMenu(
                options=options,
                placeholder="Select a character",
                custom_id="character_selection_menu"
            )
        )
    
    def create_management_buttons(self) -> ActionRow:
        """
        Create action buttons for character management.
        
        Returns:
            ActionRow with management buttons
        """
        return ActionRow(
            Button(
                style=ButtonStyle.PRIMARY,
                label="Register New Character",
                custom_id="register_new_character"
            ),
            Button(
                style=ButtonStyle.SECONDARY,
                label="View All Characters",
                custom_id="list_all_characters"
            )
        )
    
    def create_embed(self) -> Embed:
        """
        Create an embed for the character menu.
        
        Returns:
            Embed with character menu information
        """
        embed = Embed(
            title=self.title,
            description=self.description,
            color=0x3498db
        )
        
        # Add character count information
        embed.add_field(
            name="Character Count", 
            value=str(len(self.characters)),
            inline=True
        )
        
        return embed
    
    async def handle_selection(self, ctx: ComponentContext):
        """
        Handle character selection.
        
        Args:
            ctx: Component interaction context
        """
        # Get selected character ID
        selected_id = ctx.values[0]
        
        # Find the selected character
        selected_character = next(
            (char for char in self.characters if str(char.get('id', '')) == selected_id), 
            None
        )
        
        if selected_character and self.on_select:
            await self.on_select(selected_character)
        else:
            await ctx.send("Invalid character selection.", ephemeral=True)