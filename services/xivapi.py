"""
Service for interacting with the XIVAPI.
Documentation: https://xivapi.com/docs
"""
import logging
import aiohttp
from typing import Dict, List, Any, Optional, Union

from config import load_config
from services.api_cache import cached

# Logger
logger = logging.getLogger("ffxiv_bot")

# Base API URL
BASE_URL = "https://xivapi.com"

class XIVAPI:
    """Client for the XIVAPI."""
    
    def __init__(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the XIVAPI client.
        
        Args:
            api_key: Optional XIVAPI key for higher rate limits
            session: Optional aiohttp session for making requests
        """
        config = load_config()
        self.api_key = api_key or config.xivapi_key
        
        self.session = session or aiohttp.ClientSession(
            headers={"User-Agent": "FFXIV Discord Bot/1.0"}
        )
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the XIVAPI.
        
        Args:
            endpoint: API endpoint to request
            params: Query parameters for the request
            
        Returns:
            JSON response as a dictionary
        """
        url = f"{BASE_URL}/{endpoint}"
        
        # Add API key to params if available
        if self.api_key:
            params = params or {}
            params["private_key"] = self.api_key
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Error accessing XIVAPI ({url}): {e}")
            raise
    
    @cached("xivapi:servers", ttl=86400 * 7)  # Cache for 7 days
    async def get_servers(self) -> List[str]:
        """
        Get a list of all game servers.
        
        Returns:
            List of server names
        """
        response = await self._make_request("servers")
        return response
    
    @cached("xivapi:character_search", ttl=3600)  # Cache for 1 hour
    async def search_character(self, name: str, server: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for a character by name and optionally server.
        
        Args:
            name: Character name
            server: Optional server name
            
        Returns:
            Search results
        """
        params = {"name": name}
        
        if server:
            params["server"] = server
        
        return await self._make_request("character/search", params)
    
    @cached("xivapi:character", ttl=3600)  # Cache for 1 hour
    async def get_character(self, lodestone_id: str, extended: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            extended: Whether to include extended data (achievements, friends, etc.)
            
        Returns:
            Character information
        """
        params = {
            "extended": 1 if extended else 0,
            "data": "AC,FR,FC,PVP,MIMO" if extended else ""  # Achievements, Friends, FC, PVP, Mounts/Minions
        }
        
        return await self._make_request(f"character/{lodestone_id}", params)
    
    @cached("xivapi:quest", ttl=86400 * 7)  # Cache for 7 days
    async def get_quest(self, quest_id: int) -> Dict[str, Any]:
        """
        Get information about a specific quest.
        
        Args:
            quest_id: Quest ID to look up
            
        Returns:
            Quest information
        """
        return await self._make_request(f"Quest/{quest_id}")
    
    @cached("xivapi:class_job", ttl=86400 * 7)  # Cache for 7 days
    async def get_class_job(self, class_job_id: int) -> Dict[str, Any]:
        """
        Get information about a specific class/job.
        
        Args:
            class_job_id: Class/Job ID to look up
            
        Returns:
            Class/Job information
        """
        return await self._make_request(f"ClassJob/{class_job_id}")
    
    @cached("xivapi:msq_quests", ttl=86400 * 7)  # Cache for 7 days
    async def get_msq_quests(self) -> List[Dict[str, Any]]:
        """
        Get a list of MSQ quests.
        
        Returns:
            List of MSQ quests
        """
        # Search for quests with the MSQ category
        params = {
            "indexes": "Quest",
            "filters": "JournalGenre.ID=1",  # MSQ journal category
            "columns": "ID,Name,ClassJobLevel0,ExpLevel,JournalGenre.Name,Banner",
            "limit": 1000  # Get a large number to ensure we get all MSQ quests
        }
        
        response = await self._make_request("search", params)
        return response.get("Results", [])
    
    @cached("xivapi:expansion_quests", ttl=86400 * 7)  # Cache for 7 days
    async def get_expansion_msq_quests(self, expansion_id: int) -> List[Dict[str, Any]]:
        """
        Get MSQ quests for a specific expansion.
        
        Args:
            expansion_id: Expansion ID (2=ARR, 3=HW, 4=SB, 5=ShB, 6=EW)
            
        Returns:
            List of MSQ quests for the expansion
        """
        # Map expansion IDs to level ranges
        level_ranges = {
            2: "1,50",    # ARR
            3: "50,60",   # Heavensward
            4: "60,70",   # Stormblood
            5: "70,80",   # Shadowbringers
            6: "80,90",   # Endwalker
            7: "90,100"   # Dawntrail
        }
        
        level_range = level_ranges.get(expansion_id, "1,100")
        min_level, max_level = level_range.split(",")
        
        # Search for MSQ quests within the appropriate level range
        params = {
            "indexes": "Quest",
            "filters": f"JournalGenre.ID=1,ExpLevel>={min_level},ExpLevel<={max_level}",
            "columns": "ID,Name,ClassJobLevel0,ExpLevel,JournalGenre.Name,Banner",
            "limit": 1000
        }
        
        response = await self._make_request("search", params)
        return response.get("Results", [])

    async def verify_character_ownership(self, lodestone_id: str, discord_id: str) -> bool:
        """
        Verify character ownership via lodestone profile.
        
        This checks if the discord ID appears in the character's profile or status.
        
        Args:
            lodestone_id: Character's Lodestone ID
            discord_id: Discord user ID to verify
            
        Returns:
            True if verification passes, False otherwise
        """
        character = await self.get_character(lodestone_id)
        
        # Check if character data exists
        if not character or "Character" not in character:
            return False
        
        # Get profile and bio information
        char_data = character.get("Character", {})
        bio = char_data.get("Bio", "")
        
        # If user put their discord ID in their bio, that's a match
        if discord_id in bio:
            return True
        
        return False

    async def get_character_summary(self, lodestone_id: str) -> Dict[str, Any]:
        """
        Get a summary of character information for display.
        
        Args:
            lodestone_id: Character's Lodestone ID
            
        Returns:
            Summarized character information
        """
        character = await self.get_character(lodestone_id)
        
        # Check if character data exists
        if not character or "Character" not in character:
            return {"error": "Character not found"}
        
        char_data = character.get("Character", {})
        
        # Build the summary
        summary = {
            "id": char_data.get("ID"),
            "name": char_data.get("Name"),
            "server": char_data.get("Server"),
            "avatar": char_data.get("Avatar"),
            "portrait": char_data.get("Portrait"),
            "title": char_data.get("Title", {}).get("Name"),
            "race": char_data.get("Race", {}).get("Name"),
            "clan": char_data.get("Tribe", {}).get("Name"),
            "gender": "♂" if char_data.get("Gender") == 1 else "♀",
            "level": char_data.get("ActiveClassJob", {}).get("Level"),
            "job": char_data.get("ActiveClassJob", {}).get("UnlockedState", {}).get("Name"),
            "jobs": {},
            "free_company": None,
            "grand_company": None,
        }
        
        # Add all jobs and levels
        for job in char_data.get("ClassJobs", []):
            unlocked = job.get("UnlockedState", {})
            job_name = unlocked.get("Name")
            if job_name:
                summary["jobs"][job_name] = job.get("Level")
        
        # Add FC info if available
        if "FreeCompany" in character and character["FreeCompany"]:
            fc = character["FreeCompany"]
            summary["free_company"] = {
                "name": fc.get("Name"),
                "tag": fc.get("Tag")
            }
        
        # Add GC info if available
        if char_data.get("GrandCompany", {}).get("Name"):
            summary["grand_company"] = {
                "name": char_data.get("GrandCompany", {}).get("Name"),
                "rank": char_data.get("GrandCompanyRank", {}).get("Name")
            }
        
        return summary