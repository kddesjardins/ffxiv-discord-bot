"""
Recommendation engine for FFXIV mounts, minions, and content.
"""
import logging
import random
from typing import Dict, List, Any, Optional, Tuple

from services.ffxivcollect import FFXIVCollectAPI
from services.xivapi import XIVAPI

# Logger
logger = logging.getLogger("ffxiv_bot")

class RecommendationEngine:
    """Engine for generating recommendations for FFXIV content based on character data."""
    
    def __init__(self, ffxivcollect_api: FFXIVCollectAPI, xivapi: XIVAPI):
        """
        Initialize the recommendation engine.
        
        Args:
            ffxivcollect_api: FFXIVCollect API client
            xivapi: XIVAPI client
        """
        self.ffxivcollect = ffxivcollect_api
        self.xivapi = xivapi
    
    async def get_mount_recommendations(self, lodestone_id: str, count: int = 5, 
                                       use_msq_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Get mount recommendations for a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            count: Number of recommendations to return
            use_msq_progress: Whether to consider MSQ progress for recommendations
            
        Returns:
            List of recommended mounts with source info
        """
        # Get character's missing mounts
        missing_mounts = await self.ffxivcollect.get_missing_mounts(lodestone_id)
        
        # If no missing mounts, return empty list
        if not missing_mounts:
            return []
        
        # If considering MSQ progress, filter out mounts from content beyond current MSQ
        if use_msq_progress:
            # Get character summary to check MSQ progress
            character = await self.xivapi.get_character_summary(lodestone_id)
            
            # Get MSQ progress (fall back to level-based filtering if not available)
            msq_id = None
            if "error" not in character:
                # Check for progress from character data (would need to be stored in our DB)
                # For this prototype, use level as a proxy for MSQ progress
                level = character.get("level", 0)
                
                # Filter mounts based on level requirements
                filtered_mounts = []
                for mount in missing_mounts:
                    # If the mount has a level requirement in its sources
                    sources = mount.get("sources", [])
                    accessible = True
                    
                    for source in sources:
                        # If the source has a level that's too high, mark as inaccessible
                        if "type" in source and source["type"] in ["Dungeon", "Trial", "Raid"]:
                            if "related_duty" in source and source["related_duty"]:
                                if "level" in source["related_duty"] and source["related_duty"]["level"] > level:
                                    accessible = False
                                    break
                    
                    if accessible:
                        filtered_mounts.append(mount)
                
                # If filtering removed all mounts, fall back to full list
                if filtered_mounts:
                    missing_mounts = filtered_mounts
        
        # Filter to farmable mounts
        farmable_mounts = []
        for mount in missing_mounts:
            # Check if mount is farmable (has a combat source)
            sources = mount.get("sources", [])
            source_types = [s.get("type", "") for s in sources]
            
            if any(t in ["Dungeon", "Trial", "Raid", "FATE", "Special"] for t in source_types):
                farmable_mounts.append(mount)
        
        # If no farmable mounts, return empty list
        if not farmable_mounts:
            return []
        
        # Sort by drop rate (if available) and prioritize easier content
        sorted_mounts = sorted(
            farmable_mounts,
            key=lambda m: (
                # Lower priority for mounts with very low drop rates
                sum([s.get("drop_rate", 0) or 5 for s in m.get("sources", [])]) or 5,
                # Higher priority for soloable content
                sum([1 if s.get("type") == "Dungeon" else 0 for s in m.get("sources", [])]),
            ),
            reverse=True
        )
        
        # Return the top recommendations
        recommendations = sorted_mounts[:count]
        
        # Add detailed information for each recommendation
        detailed_recommendations = []
        for mount in recommendations:
            sources = mount.get("sources", [])
            source_info = []
            
            for source in sources:
                if source.get("type") in ["Dungeon", "Trial", "Raid", "FATE", "Special"]:
                    source_data = {
                        "type": source.get("type"),
                        "text": source.get("text", ""),
                    }
                    
                    # Add duty info if available
                    if "related_duty" in source and source["related_duty"]:
                        duty = source["related_duty"]
                        source_data["duty_name"] = duty.get("name", "")
                        source_data["duty_level"] = duty.get("level", 0)
                    
                    # Add drop rate if available
                    if "drop_rate" in source:
                        source_data["drop_rate"] = source.get("drop_rate", 0)
                    
                    source_info.append(source_data)
            
            detailed_mount = {
                "id": mount.get("id"),
                "name": mount.get("name"),
                "description": mount.get("description", ""),
                "enhanced_description": mount.get("enhanced_description", ""),
                "image": mount.get("image"),
                "sources": source_info,
            }
            
            detailed_recommendations.append(detailed_mount)
        
        return detailed_recommendations
    
    async def get_minion_recommendations(self, lodestone_id: str, count: int = 5, 
                                        use_msq_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Get minion recommendations for a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            count: Number of recommendations to return
            use_msq_progress: Whether to consider MSQ progress for recommendations
            
        Returns:
            List of recommended minions with source info
        """
        # Get character's missing minions
        missing_minions = await self.ffxivcollect.get_missing_minions(lodestone_id)
        
        # If no missing minions, return empty list
        if not missing_minions:
            return []
        
        # If considering MSQ progress, filter out minions from content beyond current MSQ
        if use_msq_progress:
            # Get character summary to check MSQ progress
            character = await self.xivapi.get_character_summary(lodestone_id)
            
            # Get MSQ progress (fall back to level-based filtering if not available)
            msq_id = None
            if "error" not in character:
                # For this prototype, use level as a proxy for MSQ progress
                level = character.get("level", 0)
                
                # Filter minions based on level requirements
                filtered_minions = []
                for minion in missing_minions:
                    # If the minion has a level requirement in its sources
                    sources = minion.get("sources", [])
                    accessible = True
                    
                    for source in sources:
                        # If the source has a level that's too high, mark as inaccessible
                        if "type" in source and source["type"] in ["Dungeon", "Trial", "Raid"]:
                            if "related_duty" in source and source["related_duty"]:
                                if "level" in source["related_duty"] and source["related_duty"]["level"] > level:
                                    accessible = False
                                    break
                    
                    if accessible:
                        filtered_minions.append(minion)
                
                # If filtering removed all minions, fall back to full list
                if filtered_minions:
                    missing_minions = filtered_minions
        
        # Filter to farmable minions
        farmable_minions = []
        for minion in missing_minions:
            # Check if minion is farmable (has a combat source)
            sources = minion.get("sources", [])
            source_types = [s.get("type", "") for s in sources]
            
            if any(t in ["Dungeon", "Trial", "Raid", "FATE", "Special"] for t in source_types):
                farmable_minions.append(minion)
        
        # If no farmable minions, return empty list
        if not farmable_minions:
            return []
        
        # Sort by drop rate (if available) and prioritize easier content
        sorted_minions = sorted(
            farmable_minions,
            key=lambda m: (
                # Lower priority for minions with very low drop rates
                sum([s.get("drop_rate", 0) or 5 for s in m.get("sources", [])]) or 5,
                # Higher priority for soloable content
                sum([1 if s.get("type") == "Dungeon" else 0 for s in m.get("sources", [])]),
            ),
            reverse=True
        )
        
        # Return the top recommendations
        recommendations = sorted_minions[:count]
        
        # Add detailed information for each recommendation
        detailed_recommendations = []
        for minion in recommendations:
            sources = minion.get("sources", [])
            source_info = []
            
            for source in sources:
                if source.get("type") in ["Dungeon", "Trial", "Raid", "FATE", "Special"]:
                    source_data = {
                        "type": source.get("type"),
                        "text": source.get("text", ""),
                    }
                    
                    # Add duty info if available
                    if "related_duty" in source and source["related_duty"]:
                        duty = source["related_duty"]
                        source_data["duty_name"] = duty.get("name", "")
                        source_data["duty_level"] = duty.get("level", 0)
                    
                    # Add drop rate if available
                    if "drop_rate" in source:
                        source_data["drop_rate"] = source.get("drop_rate", 0)
                    
                    source_info.append(source_data)
            
            detailed_minion = {
                "id": minion.get("id"),
                "name": minion.get("name"),
                "description": minion.get("description", ""),
                "enhanced_description": minion.get("enhanced_description", ""),
                "image": minion.get("image"),
                "tooltip": minion.get("tooltip", ""),
                "sources": source_info,
            }
            
            detailed_recommendations.append(detailed_minion)
        
        return detailed_recommendations
    
    async def get_group_recommendations(self, character_ids: List[str]) -> Dict[str, Any]:
        """
        Get recommendations for a group of characters.
        
        Args:
            character_ids: List of Lodestone IDs for characters in the group
            
        Returns:
            Dictionary with group recommendations
        """
        # Calculate which mounts/minions everyone is missing
        missing_by_all_mounts = {}
        missing_by_all_minions = {}
        
        # Track which characters we successfully processed
        processed_characters = []
        
        # Process each character
        for lodestone_id in character_ids:
            try:
                # Get character's missing mounts
                char_missing_mounts = await self.ffxivcollect.get_missing_mounts(lodestone_id)
                char_missing_minions = await self.ffxivcollect.get_missing_minions(lodestone_id)
                
                # Add to tracking
                for mount in char_missing_mounts:
                    mount_id = mount.get("id")
                    if mount_id not in missing_by_all_mounts:
                        missing_by_all_mounts[mount_id] = {
                            "mount": mount,
                            "characters": []
                        }
                    missing_by_all_mounts[mount_id]["characters"].append(lodestone_id)
                
                for minion in char_missing_minions:
                    minion_id = minion.get("id")
                    if minion_id not in missing_by_all_minions:
                        missing_by_all_minions[minion_id] = {
                            "minion": minion,
                            "characters": []
                        }
                    missing_by_all_minions[minion_id]["characters"].append(lodestone_id)
                
                processed_characters.append(lodestone_id)
                
            except Exception as e:
                logger.error(f"Error processing character {lodestone_id}: {e}")
        
        # Sort by number of characters missing each item (descending)
        sorted_mounts = sorted(
            missing_by_all_mounts.values(),
            key=lambda m: len(m["characters"]),
            reverse=True
        )
        
        sorted_minions = sorted(
            missing_by_all_minions.values(),
            key=lambda m: len(m["characters"]),
            reverse=True
        )
        
        # Filter to just farmable content
        farmable_mounts = [
            m for m in sorted_mounts 
            if any(s.get("type") in ["Dungeon", "Trial", "Raid"] 
                  for s in m["mount"].get("sources", []))
        ]
        
        farmable_minions = [
            m for m in sorted_minions 
            if any(s.get("type") in ["Dungeon", "Trial", "Raid"] 
                  for s in m["minion"].get("sources", []))
        ]
        
        # Return the recommendations
        return {
            "processed_characters": processed_characters,
            "total_characters": len(character_ids),
            "mount_recommendations": farmable_mounts[:5],
            "minion_recommendations": farmable_minions[:5]
        }
    
    def get_content_difficulty_score(self, content_type: str, level: int) -> int:
        """
        Calculate a difficulty score for content.
        
        Args:
            content_type: Type of content (Dungeon, Trial, Raid, etc.)
            level: Content level
            
        Returns:
            Difficulty score (higher = more difficult)
        """
        # Base difficulty by content type
        base_difficulty = {
            "Dungeon": 1,
            "Trial": 3,
            "Raid": 5,
            "Alliance Raid": 4,
            "Ultimate Raid": 10,
            "Deep Dungeon": 2,
            "Eureka": 3,
            "Bozja": 3,
            "FATE": 1,
        }.get(content_type, 2)
        
        # Adjust for level
        if level <= 50:
            level_modifier = 0
        elif level <= 60:
            level_modifier = 1
        elif level <= 70:
            level_modifier = 2
        elif level <= 80:
            level_modifier = 3
        else:
            level_modifier = 4
        
        return base_difficulty + level_modifier