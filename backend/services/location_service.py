import httpx
from typing import Optional, Dict, List, Tuple
import logging
import requests
import xml.etree.ElementTree as ET
logger = logging.getLogger(__name__)

class LocationService:
    #Luzerner API
    BASE_URL = "https://svc.geo.lu.ch/locationfinder/api/v1/lookup" 
    


    
    async def resolve_location(
        self, 
        query: str, 
        location_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Resolve location to coordinates
        
        Args:
            query: Search term (address, place name, EGID, EGRID, etc.)
            location_type: Optional filter - Adresse, Grundstück, Gemeinde, Ort, EGID, EGRID
        
        Returns:
            List of location results with coordinates
        """
        params = {
            "query": query,
            "limit": 10
        }
        
        # Add type filter if specified
        if location_type:
            params["filter"] = f"type:{location_type}"
        
        try:
            logger.info(f"LocationFinder query: {query} (type: {location_type})")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
                results = response.json()
                locs = results.get("locs", [])
                logger.info(f"LocationFinder found {len(locs)} locations")
                return locs
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LocationFinder: {e}")
            raise Exception(f"LocationFinder API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error to LocationFinder: {e}")
            raise Exception(f"LocationFinder request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in resolve_location: {e}")
            raise
    
    def extract_coordinates(self, location_result: Dict) -> Tuple[float, float]:
        """Extract center coordinates from location result"""
        cx = location_result.get('cx')
        cy = location_result.get('cy')
        
        if cx is None or cy is None:
            raise ValueError("Location result missing coordinates")
        
        return (float(cx), float(cy))
    
    def generate_map_url(
        self, 
        map_id: List, 
        coords: Tuple[float, float], 
        add_marker: bool = True
    ) -> str:
        """
        Generate webmap URL with coordinates
        
        Args:
            map_id: Map identifier 
            coords: Tuple of (x, y) coordinates in LV95
            add_marker: Whether to add a marker at the location
        
        Returns:
            URL to the webmap
        """
        cx, cy = coords

      
     
        
        # Round coordinates to integers
        cx = int(round(cx))
        cy = int(round(cy))
        
        # Build URL - format: https://map.geo.lu.ch/{map_id}?FOCUS=x:y:zoom&marker
        url = f"https://map.geo.lu.ch{map_id}?FOCUS={cx}:{cy}:4515"
       
        
        if add_marker:
            url += "&marker"
        
        return url


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        service = LocationService()
        
        # Test searches
        queries = [
            ("Bahnhof Luzern", None),
            ("Mürgi 1.1, 6025 Neudorf", "Adresse"),
            ("Sursee", "Gemeinde"),
        ]
        
        for query, loc_type in queries:
            print(f"\n{'='*60}")
            print(f"Testing: {query} (type: {loc_type})")
            print('='*60)
            
            try:
                results = await service.resolve_location(query, loc_type)
                print(f"Found {len(results)} results")
                
                if results:
                    result = results[0]
                    print(f"\nTop result:")
                    print(f"  Name: {result.get('name')}")
                    print(f"  Type: {result.get('type')}")
                    
                    coords = service.extract_coordinates(result)
                    print(f"  Coordinates: {coords}")
                    
                    map_url = service.generate_map_url("grundbuchplan", coords)
                    print(f"  Map URL: {map_url}")
                else:
                    print("No results found")
                    
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
    
    asyncio.run(test())