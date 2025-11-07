import httpx
from typing import Optional, Dict, List

class LocationService:
    BASE_URL = "https://svc.geo.lu.ch/locationfinder/api/v1/lookup"
    
    async def resolve_location(self, query: str, location_type: Optional[str] = None) -> List[Dict]:
        """
        Resolve location to coordinates
        location_type: Adresse, Grundstück, Gemeinde, Ort, EGID, EGRID, etc.
        """
        params = {
            "query": query,
            "limit": 10
        }
        
        if location_type:
            params["filter"] = f"type:{location_type}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
    
    def extract_coordinates(self, location_result: Dict) -> tuple:
        """Extract center coordinates from location result"""
        return (location_result.get('cx'), location_result.get('cy'))
    
    def generate_map_url(self, map_id: str, coords: tuple, add_marker: bool = True) -> str:
        """Generate webmap URL with coordinates"""
        cx, cy = coords
        url = f"https://map.geo.lu.ch/{map_id}?FOCUS={cx}:{cy}:4515"
        if add_marker:
            url += "&marker"
        return url

# Test
if __name__ == "__main__":
    import asyncio
    service = LocationService()
    results = asyncio.run(service.resolve_location("Bahnhof Luzern", "Adresse"))
    print(results)