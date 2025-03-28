"""
Progress model for tracking character progression in FFXIV.
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from models.base import BaseModel

class Progress(BaseModel):
    """FFXIV Character Progress model."""
    __tablename__ = 'character_progress'
    
    # Character association
    character_id = Column(UUID(as_uuid=True), ForeignKey('characters.id'), nullable=False)
    character = relationship("Character", back_populates="progress")
    
    # Progress type (MSQ, expansion, relic, etc.)
    progress_type = Column(String(50), nullable=False)
    
    # The specific content being tracked
    content_name = Column(String(100), nullable=False)
    content_id = Column(Integer, nullable=True)  # External ID if applicable
    
    # Progress status
    status = Column(String(50), nullable=False)  # 'completed', 'in_progress', 'not_started'
    current_step = Column(String(100), nullable=True)
    current_step_id = Column(Integer, nullable=True)
    
    # Percentage completion (0-100)
    completion_percentage = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Additional data as JSON
    details = Column(JSON, nullable=True)
    
    def is_complete(self) -> bool:
        """Check if this progress is marked as complete."""
        return self.status == 'completed' or self.completion_percentage >= 100
    
    @property
    def display_status(self) -> str:
        """Get a user-friendly status display."""
        if self.is_complete():
            return "✅ Completed"
        elif self.status == 'in_progress':
            return f"🔄 In Progress ({self.completion_percentage}%)"
        else:
            return "❌ Not Started"