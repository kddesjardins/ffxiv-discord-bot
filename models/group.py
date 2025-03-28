"""
Group model for organizing FFXIV characters.
"""
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from models.base import BaseModel
from models.character import character_group

class Group(BaseModel):
    """FFXIV Character Group model."""
    __tablename__ = 'groups'
    
    # Group information
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Discord association
    guild_id = Column(String(20), nullable=False)
    created_by = Column(String(20), nullable=False)  # Discord user ID
    
    # Group settings
    icon_url = Column(String(255), nullable=True)
    color = Column(String(10), nullable=True)  # Hex color code
    is_default = Column(Boolean, default=False)
    
    # Permission settings
    manager_role_ids = Column(ARRAY(String), nullable=True)  # Role IDs that can manage this group
    view_role_ids = Column(ARRAY(String), nullable=True)     # Role IDs that can view this group
    
    # Additional settings as JSON
    settings = Column(JSON, nullable=True)
    
    # Relationships
    characters = relationship("Character", secondary=character_group, back_populates="groups")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary including relationships."""
        result = super().to_dict()
        
        # Add character names
        result['character_names'] = [character.full_name for character in self.characters]
        result['character_count'] = len(self.characters)
        
        return result
    
    def can_manage(self, user_id: str, user_roles: List[str]) -> bool:
        """Check if a user can manage this group."""
        # The creator can always manage
        if self.created_by == user_id:
            return True
        
        # Check if user has any of the manager roles
        if self.manager_role_ids:
            return any(role_id in self.manager_role_ids for role_id in user_roles)
        
        return False
    
    def can_view(self, user_id: str, user_roles: List[str]) -> bool:
        """Check if a user can view this group."""
        # If they can manage, they can view
        if self.can_manage(user_id, user_roles):
            return True
        
        # Check if the group is viewable by specific roles
        if self.view_role_ids:
            return any(role_id in self.view_role_ids for role_id in user_roles)
        
        # Default groups are viewable by everyone
        return self.is_default