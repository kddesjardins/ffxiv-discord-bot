"""
Character model for storing FFXIV character data.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Table
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from models.base import BaseModel, Base

# Association table for character-group many-to-many relationship
character_group = Table(
    'character_group',
    Base.metadata,
    Column('character_id', UUID(as_uuid=True), ForeignKey('characters.id'), primary_key=True),
    Column('group_id', UUID(as_uuid=True), ForeignKey('groups.id'), primary_key=True)
)

class Character(BaseModel):
    """FFXIV Character model."""
    __tablename__ = 'characters'
    
    # Character identification
    name = Column(String(100), nullable=False)
    server = Column(String(50), nullable=False)
    lodestone_id = Column(String(50), nullable=True, unique=True)
    
    # Discord association
    discord_user_id = Column(String(20), nullable=True)
    is_primary = Column(Boolean, default=False)
    
    # Character details
    avatar_url = Column(String(255), nullable=True)
    portrait_url = Column(String(255), nullable=True)
    title = Column(String(100), nullable=True)
    race = Column(String(50), nullable=True)
    clan = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)
    
    # Classes/Jobs
    active_class_job = Column(String(50), nullable=True)
    class_jobs = Column(JSON, nullable=True)  # JSON with job levels
    
    # MSQ progression
    msq_progress = Column(String(100), nullable=True)
    msq_id = Column(Integer, nullable=True)
    
    # Collection data
    mounts = Column(ARRAY(Integer), nullable=True)
    minions = Column(ARRAY(Integer), nullable=True)
    
    # Last verified/updated with API
    last_verified = Column(DateTime, nullable=True)
    
    # Relationships
    groups = relationship("Group", secondary=character_group, back_populates="characters")
    progress = relationship("Progress", back_populates="character", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary including relationships."""
        result = super().to_dict()
        
        # Add group names
        result['group_names'] = [group.name for group in self.groups]
        
        return result
    
    @property
    def full_name(self) -> str:
        """Get character's full name with server."""
        return f"{self.name} ({self.server})"
    
    @property
    def lodestone_url(self) -> Optional[str]:
        """Get character's Lodestone URL."""
        if self.lodestone_id:
            return f"https://na.finalfantasyxiv.com/lodestone/character/{self.lodestone_id}/"
        return None