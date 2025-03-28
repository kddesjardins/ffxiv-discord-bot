"""
Service for interacting with the FFXIVCollect API.
Documentation: https://ffxivcollect.com/api/docs
"""
import logging
import aiohttp
from typing import Dict, List, Any, Optional, Union

from services.api_cache import cached

# Logger
logger = logging.getLogger("ffxiv_bot")

# Base API URL
BASE_URL = "https://ffxivcollect.com/api/v1"

class FFXIVCollectAPI:
    """Client for the FFXIVCollect API."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the FFXIVCollect API client.
        
        Args:
            session: Optional aiohttp session for making requests
        """
        self.session = session or aiohttp.ClientSession(
            headers={"User-Agent": "FFXIV Discord Bot/1.0"}
        )
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the FFXIVCollect API.
        
        Args:
            endpoint: API endpoint to request
            params: Query parameters for the request
            
        Returns:
            JSON response as a dictionary
        """
        url = f"{BASE_URL}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Error accessing FFXIVCollect API ({url}): {e}")
            raise
    
    @cached("ffxivcollect:mounts", ttl=86400)  # Cache for 24 hours
    async def get_mounts(self, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """
        Get available mounts from FFXIVCollect.
        
        Args:
            limit: Maximum number of results (default: 1000)
            offset: Result offset for pagination
            
        Returns:
            Dictionary containing mount information
        """
        return await self._make_request("mounts", {"limit": limit, "offset": offset})
    
    @cached("ffxivcollect:minions", ttl=86400)  # Cache for 24 hours
    async def get_minions(self, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """
        Get available minions from FFXIVCollect.
        
        Args:
            limit: Maximum number of results (default: 1000)
            offset: Result offset for pagination
            
        Returns:
            Dictionary containing minion information
        """
        return await self._make_request("minions", {"limit": limit, "offset": offset})
    
    @cached("ffxivcollect:mount", ttl=86400)
    async def get_mount(self, mount_id: int) -> Dict[str, Any]:
        """
        Get information about a specific mount.
        
        Args:
            mount_id: Mount ID to look up
            
        Returns:
            Dictionary containing mount information
        """
        return await self._make_request(f"mounts/{mount_id}")
    
    @cached("ffxivcollect:minion", ttl=86400)
    async def get_minion(self, minion_id: int) -> Dict[str, Any]:
        """
        Get information about a specific minion.
        
        Args:
            minion_id: Minion ID to look up
            
        Returns:
            Dictionary containing minion information
        """
        return await self._make_request(f"minions/{minion_id}")
    
    @cached("ffxivcollect:character", ttl=3600)  # Cache for 1 hour
    async def get_character_collections(self, lodestone_id: str) -> Dict[str, Any]:
        """
        Get collection information for a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            
        Returns:
            Dictionary containing character collection information
        """
        return await self._make_request(f"characters/{lodestone_id}")
    
    async def get_mount_completion(self, lodestone_id: str) -> Dict[str, Any]:
        """
        Get detailed mount completion for a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            
        Returns:
            Dictionary with mount completion information
        """
        collections = await self.get_character_collections(lodestone_id)
        return collections.get("mounts", {})
    
    async def get_minion_completion(self, lodestone_id: str) -> Dict[str, Any]:
        """
        Get detailed minion completion for a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            
        Returns:
            Dictionary with minion completion information
        """
        collections = await self.get_character_collections(lodestone_id)
        return collections.get("minions", {})
    
    async def search_mounts(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for mounts by name.
        
        Args:
            query: Search query
            
        Returns:
            List of matching mounts
        """
        mounts = await self.get_mounts()
        results = []
        
        query = query.lower()
        for mount in mounts.get("results", []):
            if query in mount.get("name", "").lower():
                results.append(mount)
                
        return results
    
    async def search_minions(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for minions by name.
        
        Args:
            query: Search query
            
        Returns:
            List of matching minions
        """
        minions = await self.get_minions()
        results = []
        
        query = query.lower()
        for minion in minions.get("results", []):
            if query in minion.get("name", "").lower():
                results.append(minion)
                
        return results
    
    async def get_farmable_mounts(self) -> List[Dict[str, Any]]:
        """
        Get mounts that can be farmed.
        
        Returns:
            List of farmable mounts
        """
        mounts = await self.get_mounts()
        farmable = []
        
        for mount in mounts.get("results", []):
            # Check sources that are typically farmable
            sources = mount.get("sources", [])
            source_types = [s.get("type", "") for s in sources]
            
            if any(t in ["Dungeon", "Trial", "Raid", "Special"] for t in source_types):
                farmable.append(mount)
                
        return farmable
    
    async def get_farmable_minions(self) -> List[Dict[str, Any]]:
        """
        Get minions that can be farmed.
        
        Returns:
            List of farmable minions
        """
        minions = await self.get_minions()
        farmable = []
        
        for minion in minions.get("results", []):
            # Check sources that are typically farmable
            sources = minion.get("sources", [])
            source_types = [s.get("type", "") for s in sources]
            
            if any(t in ["Dungeon", "Trial", "Raid", "Special"] for t in source_types):
                farmable.append(minion)
                
        return farmable
    
    async def get_missing_mounts(self, lodestone_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of mounts that the character is missing.
        
        Args:
            lodestone_id: Character's Lodestone ID
            
        Returns:
            List of mounts the character doesn't have
        """
        # Get character's mount collection
        collection = await self.get_mount_completion(lodestone_id)
        owned_ids = collection.get("ids", [])
        
        # Get all mounts
        all_mounts = await self.get_mounts()
        
        # Filter to only include mounts the character doesn't have
        missing = []
        for mount in all_mounts.get("results", []):
            if mount.get("id") not in owned_ids:
                missing.append(mount)
                
        return missing
    
    async def get_missing_minions(self, lodestone_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of minions that the character is missing.
        
        Args:
            lodestone_id: Character's Lodestone ID
            
        Returns:
            List of minions the character doesn't have
        """
        # Get character's minion collection
        collection = await self.get_minion_completion(lodestone_id)
        owned_ids = collection.get("ids", [])
        
        # Get all minions
        all_minions = await self.get_minions()
        
        # Filter to only include minions the character doesn't have
        missing = []
        for minion in all_minions.get("results", []):
            if minion.get("id") not in owned_ids:
                missing.append(minion)
                
        return missing