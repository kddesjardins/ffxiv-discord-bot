"""
XIVAPI Client for the FFXIV Discord bot.
"""
import logging
import aiohttp
import os
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger("ffxiv_bot")

class XIVAPIClient:
    """Client for interacting with XIVAPI."""
    
    BASE_URL = "https://xivapi.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the XIVAPI client.
        
        Args:
            api_key: Optional API key for XIVAPI
        """
        self.api_key = api_key or os.getenv("XIVAPI_KEY")
        self.session = None
    
    async def initialize(self):
        """Initialize HTTP session for API requests."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": "FFXIV Discord Bot/1.0"}
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to XIVAPI.
        
        Args:
            endpoint: API endpoint to request
            params: Query parameters
            
        Returns:
            API response as JSON
        """
        await self.initialize()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add API key if available
        if params is None:
            params = {}
        
        if self.api_key:
            params["private_key"] = self.api_key
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    # Rate limited
                    logger.warning("Rate limited by XIVAPI")
                    return {"Error": "Rate limited by XIVAPI", "status": 429}
                
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP error accessing XIVAPI: {e.status} {e.message}")
            return {"Error": f"HTTP error: {e.status} {e.message}", "status": e.status}
            
        except aiohttp.ClientError as e:
            logger.error(f"Error accessing XIVAPI: {e}")
            return {"Error": f"Connection error: {str(e)}", "status": 0}
            
        except Exception as e:
            logger.error(f"Unexpected error accessing XIVAPI: {e}")
            return {"Error": f"Unexpected error: {str(e)}", "status": 0}
    
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
        
        return await self._request("character/search", params)
    
    async def get_character(self, lodestone_id: str, extended: bool = False) -> Dict[str, Any]:
        """
        Get detailed information about a character.
        
        Args:
            lodestone_id: Character's Lodestone ID
            extended: Whether to include extended data
            
        Returns:
            Character information
        """
        params = {
            "extended": 1 if extended else 0,
            "data": "FC,MIMO" if extended else ""  # FC = Free Company, MIMO = Minions & Mounts
        }
        
        return await self._request(f"character/{lodestone_id}", params)
    
    async def get_servers(self) -> List[str]:
        """
        Get a list of all game servers.
        
        Returns:
            List of server names
        """
        response = await self._request("servers")
        
        if isinstance(response, list):
            return response
        return []
    
    async def get_data_centers(self) -> Dict[str, List[str]]:
        """
        Get a mapping of data centers to servers.
        
        Returns:
            Dictionary with data centers as keys and lists of servers as values
        """
        response = await self._request("servers/dc")
        
        if not isinstance(response, dict) or "Error" in response:
            return {}
        return response