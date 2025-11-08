"""
Tool-calling functions for Geopard RAG - Phase 1
Provides integration with LocationFinder API and Webmap URL generation
"""

import requests
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlencode, quote


class LocationFinderTool:
    """
    LocationFinder API integration for converting location queries to coordinates
    """
    
    BASE_URL = "https://svc.geo.lu.ch/locationfinder/api/v1/lookup"
    
    SEARCH_TYPES = {
        'adresse': 'Adresse',
        'gemeinde': 'Gemeinde', 
        'ortsname': 'Ortsname',
        'flurname': 'Flurname',
        'egid': 'EGID',
        'egrid': 'EGRID',
        'parzelle': 'Parzellennummer',
        'gebaeude': 'Gebäudeversicherungsnummer'
    }
    
    def search(self, query: str, limit: int = 10, filter_type: Optional[str] = None) -> List[Dict]:
        """
        Search for locations using LocationFinder API
        
        Args:
            query: Search query (address, place name, EGID, etc.)
            limit: Maximum number of results
            filter_type: Optional filter for specific type (e.g., 'Adresse')
        
        Returns:
            List of location results with coordinates
        """
        params = {
            'query': query,
            'limit': limit
        }
        
        if filter_type:
            params['filter'] = f"type:{filter_type}"
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # API returns 'locs' array, not 'results'
            items = data.get('locs', [])
            
            results = []
            for item in items:
                results.append({
                    'id': item.get('id'),
                    'type': item.get('type'),
                    'name': item.get('name'),
                    'cx': item.get('cx'),  # Center X coordinate
                    'cy': item.get('cy'),  # Center Y coordinate
                    'xmin': item.get('xmin'),
                    'ymin': item.get('ymin'),
                    'xmax': item.get('xmax'),
                    'ymax': item.get('ymax'),
                    'fields': item.get('fields', {})
                })
            
            return results
            
        except requests.RequestException as e:
            print(f"❌ LocationFinder API error: {e}")
            return []
        except Exception as e:
            print(f"❌ LocationFinder parsing error: {e}")
            return []
    
    def get_coordinates(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a location query
        
        Returns:
            (x, y) coordinates or None if not found
        """
        results = self.search(query, limit=1)
        if results:
            result = results[0]
            return (result['cx'], result['cy'])
        return None


class WebmapURLBuilder:
    """
    Build URLs for Luzern Webmaps with zoom and marker support
    """
    
    BASE_URL = "https://map.geo.lu.ch"
    
    # Common map themes
    MAPS = {
        'grundbuchplan': 'grundbuchplan',
        'oberflaechengewaesser': 'oberflaechengewaesser/netz',
        'amtliche_vermessung': 'amtliche_vermessung',
        'hoehen': 'hoehen',
        'laerm': 'laermbelastung',
        'default': 'map'
    }
    
    def build_url(
        self, 
        map_theme: str = 'default',
        x: Optional[float] = None,
        y: Optional[float] = None,
        zoom: int = 4515,
        add_marker: bool = True
    ) -> str:
        """
        Build a webmap URL with focus and marker
        
        Args:
            map_theme: Map theme key (e.g., 'grundbuchplan')
            x, y: Coordinates (Swiss LV95)
            zoom: Zoom level (higher = more zoomed in)
            add_marker: Whether to add a marker at the location
        
        Returns:
            Complete webmap URL
        """
        map_path = self.MAPS.get(map_theme, self.MAPS['default'])
        url = f"{self.BASE_URL}/{map_path}"
        
        params = []
        
        if x is not None and y is not None:
            params.append(f"FOCUS={x:.0f}:{y:.0f}:{zoom}")
        
        if add_marker and x is not None and y is not None:
            params.append("marker")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def get_map_for_dataset(self, dataset_title: str) -> str:
        """
        Determine appropriate map theme based on dataset title
        
        Args:
            dataset_title: Title of the dataset
        
        Returns:
            Map theme key
        """
        title_lower = dataset_title.lower()
        
        if any(word in title_lower for word in ['höhe', 'terrain', 'dtm', 'dom']):
            return 'hoehen'
        elif any(word in title_lower for word in ['lärm', 'laerm', 'noise']):
            return 'laerm'
        elif any(word in title_lower for word in ['gewässer', 'gewaesser', 'wasser', 'water']):
            return 'oberflaechengewaesser'
        elif any(word in title_lower for word in ['grundbuch', 'vermessung', 'cadastre']):
            return 'grundbuchplan'
        else:
            return 'default'


class GeodatashopLinkBuilder:
    """
    Build links to Geodatashop for dataset downloads
    """
    
    OPENLY_BASE = "https://www.geo.lu.ch/openly"
    SHOP_BASE = "https://geodatenshop.lu.ch"
    
    def build_openly_link(self, metauid: str) -> str:
        """
        Build link to openly.geo.lu.ch for a dataset
        
        Args:
            metauid: Metadata UID of the dataset
        
        Returns:
            URL to openly page
        """
        return f"{self.OPENLY_BASE}/dataset/{metauid}"
    
    def build_shop_link(self, search_term: str) -> str:
        """
        Build search link to geodatashop
        
        Args:
            search_term: Search term for the shop
        
        Returns:
            URL to shop search
        """
        encoded_term = quote(search_term)
        return f"{self.SHOP_BASE}?search={encoded_term}"


class GeopardToolkit:
    """
    Complete toolkit for Geopard RAG tool-calling
    """
    
    def __init__(self):
        self.location_finder = LocationFinderTool()
        self.webmap_builder = WebmapURLBuilder()
        self.shop_builder = GeodatashopLinkBuilder()
    
    def enrich_dataset_result(
        self, 
        dataset: Dict,
        user_query: str = ""
    ) -> Dict:
        """
        Enrich a dataset search result with location data and URLs
        
        Args:
            dataset: Dataset metadata from search
            user_query: User's original query (may contain location)
        
        Returns:
            Enriched dataset with additional URLs and location data
        """
        enriched = dataset.copy()
        
        # Extract location from query if present
        location_info = None
        if user_query:
            location_info = self.extract_location_from_query(user_query)
        
        # Build webmap URL
        if location_info:
            x = location_info['cx']
            y = location_info['cy']
            map_theme = self.webmap_builder.get_map_for_dataset(dataset.get('title', ''))
            webmap_url = self.webmap_builder.build_url(
                map_theme=map_theme,
                x=x,
                y=y,
                zoom=4515,
                add_marker=True
            )
            enriched['webmap_url_with_location'] = webmap_url
            enriched['location_coordinates'] = {'x': x, 'y': y}
            enriched['location_name'] = location_info.get('name', '')
        
        # Add Geodatashop links
        metauid = dataset.get('metauid', '')
        if metauid:
            enriched['openly_link'] = self.shop_builder.build_openly_link(metauid)
        
        title = dataset.get('title', '')
        if title:
            enriched['shop_search_link'] = self.shop_builder.build_shop_link(title)
        
        return enriched
    
    def extract_location_from_query(self, query: str) -> Optional[Dict]:
        """
        Try to extract location information from user query
        
        Args:
            query: User's query string
        
        Returns:
            Location info dict or None
        """
        # Common location keywords to extract
        import re
        
        # Try direct search first
        results = self.location_finder.search(query, limit=1)
        if results:
            return results[0]
        
        # Extract potential location terms
        # Look for capitalized words that might be place names
        words = query.split()
        
        # Try common patterns
        patterns = [
            r'(Bahnhof\s+\w+)',  # Bahnhof + place
            r'(\w+straße\s+\d+)',  # Street + number
            r'(\w+strasse\s+\d+)',  # Swiss spelling
            r'(\d{4}\s+\w+)',  # Postal code + place
            r'(Gemeinde\s+\w+)',  # Municipality
            r'(in\s+(\w+))',  # in + place name
            r'(für\s+(\w+))',  # für + place name
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location_term = match.group(1)
                results = self.location_finder.search(location_term, limit=1)
                if results:
                    return results[0]
        
        # Try searching for capitalized words (potential place names)
        for word in words:
            if word and word[0].isupper() and len(word) > 3:
                results = self.location_finder.search(word, limit=1)
                if results and results[0].get('type') in ['Gemeinde', 'Ortsname', 'Adresse']:
                    return results[0]
        
        return None


# Example usage
if __name__ == "__main__":
    toolkit = GeopardToolkit()
    
    # Test LocationFinder
    print("Testing LocationFinder:")
    results = toolkit.location_finder.search("Bahnhof Luzern", limit=3)
    for r in results:
        print(f"  - {r['name']} ({r['type']}): {r['cx']}, {r['cy']}")
    
    # Test Webmap URL
    print("\nTesting Webmap URL:")
    coords = toolkit.location_finder.get_coordinates("Bahnhof Luzern")
    if coords:
        x, y = coords
        url = toolkit.webmap_builder.build_url('hoehen', x, y, zoom=4515)
        print(f"  URL: {url}")
    
    # Test enrichment
    print("\nTesting dataset enrichment:")
    sample_dataset = {
        'metauid': 'DTM2024_DST',
        'title': 'Digitales Terrainmodell 2024',
        'data_type': 'Datensatz'
    }
    enriched = toolkit.enrich_dataset_result(sample_dataset, "Bahnhof Luzern")
    print(f"  Openly: {enriched.get('openly_link')}")
    print(f"  Webmap: {enriched.get('webmap_url_with_location')}")
