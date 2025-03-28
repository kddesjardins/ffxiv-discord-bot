"""
Pagination utility for handling large lists of items in Discord interactions.
"""
from typing import List, Any, Optional, Callable, Awaitable

from interactions import (
    ComponentContext,
    Embed,
    Button,
    ButtonStyle,
    ActionRow
)

class Paginator:
    """
    Generic paginator for managing and displaying lists of items.
    """
    def __init__(
        self, 
        items: List[Any], 
        items_per_page: int = 10,
        title: str = "Items List",
        description: Optional[str] = None,
        item_formatter: Optional[Callable[[Any], str]] = None
    ):
        """
        Initialize the paginator.
        
        Args:
            items: List of items to paginate
            items_per_page: Number of items to display per page
            title: Title of the pagination embed
            description: Optional description for the embed
            item_formatter: Optional function to format individual items
        """
        self.items = items
        self.items_per_page = items_per_page
        self.title = title
        self.description = description
        self.item_formatter = item_formatter or str
        
        # Calculate total pages
        self.total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
        
        # Current page (0-indexed)
        self.current_page = 0
    
    def get_page_items(self) -> List[Any]:
        """
        Get items for the current page.
        
        Returns:
            List of items for the current page
        """
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        return self.items[start_index:end_index]
    
    def create_embed(self) -> Embed:
        """
        Create an embed for the current page.
        
        Returns:
            Embed with current page items
        """
        # Get items for current page
        page_items = self.get_page_items()
        
        # Format item list
        items_text = "\n".join(
            f"{i+1}. {self.item_formatter(item)}" 
            for i, item in enumerate(page_items)
        )
        
        # Create embed
        embed = Embed(
            title=self.title,
            description=self.description or "",
            color=0x3498db
        )
        
        # Add items to embed
        embed.add_field(
            name=f"Page {self.current_page + 1}/{self.total_pages}",
            value=items_text or "No items to display",
            inline=False
        )
        
        return embed
    
    def create_navigation_buttons(self) -> ActionRow:
        """
        Create navigation buttons for pagination.
        
        Returns:
            ActionRow with navigation buttons
        """
        buttons = []
        
        # Previous page button
        if self.current_page > 0:
            buttons.append(
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="Previous",
                    custom_id="paginator_previous"
                )
            )
        
        # Next page button
        if self.current_page < self.total_pages - 1:
            buttons.append(
                Button(
                    style=ButtonStyle.PRIMARY,
                    label="Next",
                    custom_id="paginator_next"
                )
            )
        
        return ActionRow(*buttons)
    
    def navigate(self, direction: str) -> bool:
        """
        Navigate to the next or previous page.
        
        Args:
            direction: 'next' or 'previous'
        
        Returns:
            True if navigation was successful, False otherwise
        """
        if direction == 'next' and self.current_page < self.total_pages - 1:
            self.current_page += 1
            return True
        elif direction == 'previous' and self.current_page > 0:
            self.current_page -= 1
            return True
        
        return False
    
    async def handle_interaction(
        self, 
        ctx: ComponentContext, 
        on_update: Optional[Callable[[Embed, ActionRow], Awaitable[None]]] = None
    ):
        """
        Handle pagination interaction.
        
        Args:
            ctx: Component interaction context
            on_update: Optional callback to update the message
        """
        # Determine navigation direction
        direction = 'next' if 'next' in ctx.custom_id else 'previous'
        
        # Navigate pages
        if self.navigate(direction):
            # Create updated embed and buttons
            new_embed = self.create_embed()
            new_buttons = self.create_navigation_buttons()
            
            # Update message if callback is provided
            if on_update:
                await on_update(new_embed, new_buttons)
            else:
                # Default update if no custom handler
                await ctx.edit_origin(embed=new_embed, components=[new_buttons])
        else:
            await ctx.send("No more pages to navigate.", ephemeral=True)

    @classmethod
    def from_data(
        cls, 
        data: List[Any], 
        title: str = "Items List", 
        description: Optional[str] = None,
        items_per_page: int = 10,
        item_formatter: Optional[Callable[[Any], str]] = None
    ) -> 'Paginator':
        """
        Class method to create a Paginator from a list of data.
        
        Args:
            data: List of items to paginate
            title: Title of the pagination embed
            description: Optional description for the embed
            items_per_page: Number of items per page
            item_formatter: Optional function to format individual items
        
        Returns:
            Paginator instance
        """
        return cls(
            items=data,
            title=title,
            description=description,
            items_per_page=items_per_page,
            item_formatter=item_formatter
        )