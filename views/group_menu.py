"""
Group selection and management menu view.
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

class GroupMenu:
    """
    Interactive menu for group selection and management.
    """
    def __init__(
        self, 
        groups: List[dict], 
        on_select: Optional[Callable[[str], Awaitable[None]]] = None,
        title: str = "Select a Group",
        description: str = "Choose a group from the list"
    ):
        """
        Initialize the group selection menu.
        
        Args:
            groups: List of group dictionaries
            on_select: Async callback function when a group is selected
            title: Menu title
            description: Menu description
        """
        self.groups = groups
        self.on_select = on_select
        self.title = title
        self.description = description
    
    def create_group_select(self) -> ActionRow:
        """
        Create a select menu with available groups.
        
        Returns:
            ActionRow with group selection menu
        """
        # Prepare select options
        options = []
        for group in self.groups:
            # Format option label and description
            label = group.get('name', 'Unnamed Group')
            description = (
                f"Members: {group.get('character_count', 0)} | "
                f"Created by: {group.get('created_by', 'Unknown')}"
            )
            
            options.append(
                SelectOption(
                    label=label,
                    value=str(group.get('id', '')),
                    description=description
                )
            )
        
        # Create select menu
        return ActionRow(
            SelectMenu(
                options=options,
                placeholder="Select a group",
                custom_id="group_selection_menu"
            )
        )
    
    def create_management_buttons(self) -> ActionRow:
        """
        Create action buttons for group management.
        
        Returns:
            ActionRow with management buttons
        """
        return ActionRow(
            Button(
                style=ButtonStyle.PRIMARY,
                label="Create New Group",
                custom_id="create_new_group"
            ),
            Button(
                style=ButtonStyle.SECONDARY,
                label="View All Groups",
                custom_id="list_all_groups"
            )
        )
    
    def create_embed(self) -> Embed:
        """
        Create an embed for the group menu.
        
        Returns:
            Embed with group menu information
        """
        embed = Embed(
            title=self.title,
            description=self.description,
            color=0x2ecc71
        )
        
        # Add group count and total character information
        total_characters = sum(
            group.get('character_count', 0) for group in self.groups
        )
        
        embed.add_field(
            name="Group Statistics", 
            value=(
                f"Total Groups: {len(self.groups)}\n"
                f"Total Characters: {total_characters}"
            ),
            inline=True
        )
        
        return embed
    
    async def handle_selection(self, ctx: ComponentContext):
        """
        Handle group selection.
        
        Args:
            ctx: Component interaction context
        """
        # Get selected group ID
        selected_id = ctx.values[0]
        
        # Find the selected group
        selected_group = next(
            (group for group in self.groups if str(group.get('id', '')) == selected_id), 
            None
        )
        
        if selected_group and self.on_select:
            await self.on_select(selected_group)
        else:
            await ctx.send("Invalid group selection.", ephemeral=True)