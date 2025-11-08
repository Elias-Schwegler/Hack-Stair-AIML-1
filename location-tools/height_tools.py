"""Height/Elevation tools for Swiss geodata via GeoAdmin API and swissALTI3D."""

import requests
import math
from typing import Dict, Optional, Tuple, List


class CoordinateTransformer:
    """Transform between WGS84 and Swiss LV95. Precision: <1m position, <0.5m height."""
    
    @staticmethod
    def wgs84_to_lv95(lat: float, lon: float) -> Tuple[float, float]:
        """Convert WGS84 (lat, lon) to LV95 (E, N) in meters."""
        lat_aux = (lat * 3600 - 169028.66) / 10000
        lon_aux = (lon * 3600 - 26782.5) / 10000
        
        E = 2600072.37 + 211455.93 * lon_aux - 10938.51 * lon_aux * lat_aux - \
            0.36 * lon_aux * lat_aux**2 - 44.54 * lon_aux**3
        N = 1200147.07 + 308807.95 * lat_aux + 3745.25 * lon_aux**2 + \
            76.63 * lat_aux**2 - 194.56 * lon_aux**2 * lat_aux + 119.79 * lat_aux**3
        
        return (E, N)
    
    @staticmethod
    def lv95_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
        """Convert LV95 (E, N) in meters to WGS84 (lat, lon)."""
        y_aux = (easting - 2600000) / 1000000
        x_aux = (northing - 1200000) / 1000000
        
        lon_sec = 2.6779094 + 4.728982 * y_aux + 0.791484 * y_aux * x_aux + \
                  0.1306 * y_aux * x_aux**2 - 0.0436 * y_aux**3
        lat_sec = 16.9023892 + 3.238272 * x_aux - 0.270978 * y_aux**2 - \
                  0.002528 * x_aux**2 - 0.0447 * y_aux**2 * x_aux - 0.0140 * x_aux**3
        
        return (lat_sec * 100 / 36, lon_sec * 100 / 36)


class SwissHeightAPI:
    """Query elevation via GeoAdmin API (swissALTI3D)."""
    HEIGHT_API_URL = "https://api3.geo.admin.ch/rest/services/height"
    PROFILE_API_URL = "https://api3.geo.admin.ch/rest/services/profile.json"
    
    def __init__(self):
        self.transformer = CoordinateTransformer()
    
    def get_height_at_location(self, lat: Optional[float] = None, lon: Optional[float] = None,
                              easting: Optional[float] = None, northing: Optional[float] = None) -> Optional[Dict]:
        """Get elevation at location (WGS84 lat/lon OR LV95 E/N)."""
        if lat is not None and lon is not None:
            easting, northing = self.transformer.wgs84_to_lv95(lat, lon)
        if easting is None or northing is None:
            raise ValueError("Must provide either (lat, lon) or (easting, northing)")
        
        params = {'easting': easting, 'northing': northing, 'sr': '2056'}
        
        try:
            response = requests.get(self.HEIGHT_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'height' in data:
                return {
                    'height_m': round(float(data['height']), 2),
                    'coordinates_lv95': {'easting': round(easting, 2), 'northing': round(northing, 2)},
                    'source': 'swissALTI3D',
                    'height_reference': 'LHN95'
                }
            return None
        except Exception as e:
            print(f"❌ Height API error: {e}")
            return None
    
    def get_height_profile(self, coordinates: List[Tuple[float, float]], use_wgs84: bool = True) -> Optional[Dict]:
        """Get elevation profile along path."""
        lv95_coords = [self.transformer.wgs84_to_lv95(lat, lon) for lat, lon in coordinates] if use_wgs84 else coordinates
        geom_str = str([[e, n] for e, n in lv95_coords]).replace(' ', '')
        params = {'geom': geom_str, 'sr': '2056', 'nb_points': 200}
        
        try:
            response = requests.get(self.PROFILE_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data:
                heights = [point.get('alts', {}).get('COMB', 0) for point in data]
                return {
                    'profile_points': data,
                    'num_points': len(data),
                    'min_height_m': round(min(heights), 2) if heights else None,
                    'max_height_m': round(max(heights), 2) if heights else None,
                    'height_difference_m': round(max(heights) - min(heights), 2) if heights else None,
                    'source': 'swissALTI3D'
                }
            return None
        except Exception as e:
            print(f"❌ Profile API error: {e}")
            return None


class HeightQueryToolkit:
    """Toolkit for height queries with LocationFinder integration."""
    
    def __init__(self):
        self.height_api = SwissHeightAPI()
        self.transformer = CoordinateTransformer()
    
    def query_height_by_location_name(self, location_name: str, location_finder=None) -> Optional[Dict]:
        """Query height for named location (e.g., 'Bahnhof Luzern')."""
        if location_finder is None:
            try:
                from location_tools import LocationFinderTool
                location_finder = LocationFinderTool()
            except ImportError:
                return {'success': False, 'error': 'LocationFinder not available'}
        
        results = location_finder.search(location_name, limit=1)
        if not results:
            return {'success': False, 'error': f'Location "{location_name}" not found'}
        
        location = results[0]
        height_data = self.height_api.get_height_at_location(easting=location['cx'], northing=location['cy'])
        
        if height_data:
            return {
                'success': True,
                'location_name': location['name'],
                'location_type': location['type'],
                'height_m': height_data['height_m'],
                'height_text': f"{height_data['height_m']} m ü. M.",
                'coordinates_lv95': height_data['coordinates_lv95'],
                'source': height_data['source'],
                'height_reference': height_data['height_reference']
            }
        return {'success': False, 'error': 'Could not retrieve height data'}
    
    def query_height_wgs84(self, lat: float, lon: float) -> Optional[Dict]:
        """Query height for WGS84 coordinates."""
        height_data = self.height_api.get_height_at_location(lat=lat, lon=lon)
        if height_data:
            return {'success': True, 'height_m': height_data['height_m'],
                   'height_text': f"{height_data['height_m']} m ü. M.",
                   'coordinates_wgs84': {'latitude': lat, 'longitude': lon},
                   'coordinates_lv95': height_data['coordinates_lv95'],
                   'source': height_data['source'], 'height_reference': height_data['height_reference']}
        return {'success': False, 'error': 'Could not retrieve height data'}
    
    def query_height_lv95(self, easting: float, northing: float) -> Optional[Dict]:
        """Query height for LV95 coordinates."""
        height_data = self.height_api.get_height_at_location(easting=easting, northing=northing)
        if height_data:
            return {'success': True, 'height_m': height_data['height_m'],
                   'height_text': f"{height_data['height_m']} m ü. M.",
                   'coordinates_lv95': height_data['coordinates_lv95'],
                   'source': height_data['source'], 'height_reference': height_data['height_reference']}
        return {'success': False, 'error': 'Could not retrieve height data'}


# Example usage
if __name__ == "__main__":
    toolkit = HeightQueryToolkit()
    
    print("Testing Height Query Tools")
    print("=" * 60)
    
    # Test 1: Query by location name
    print("\n1. Query height for Bahnhof Luzern:")
    result = toolkit.query_height_by_location_name("Bahnhof Luzern")
    if result and result.get('success'):
        print(f"   Location: {result['location_name']} ({result['location_type']})")
        print(f"   Height: {result['height_text']}")
        print(f"   Coordinates LV95: E={result['coordinates_lv95']['easting']}, N={result['coordinates_lv95']['northing']}")
    else:
        print(f"   Error: {result.get('error') if result else 'Unknown error'}")
    
    # Test 2: Query by WGS84 coordinates (Lucerne)
    print("\n2. Query height for Lucerne (WGS84: 47.0501682, 8.3093072):")
    result = toolkit.query_height_wgs84(47.0501682, 8.3093072)
    if result and result.get('success'):
        print(f"   Height: {result['height_text']}")
        print(f"   Coordinates LV95: E={result['coordinates_lv95']['easting']}, N={result['coordinates_lv95']['northing']}")
    else:
        print(f"   Error: {result.get('error') if result else 'Unknown error'}")
    
    # Test 3: Test coordinate transformation
    print("\n3. Testing coordinate transformation:")
    lat, lon = 47.0501682, 8.3093072
    e, n = CoordinateTransformer.wgs84_to_lv95(lat, lon)
    print(f"   WGS84 ({lat}, {lon}) -> LV95 ({e:.2f}, {n:.2f})")
    lat2, lon2 = CoordinateTransformer.lv95_to_wgs84(e, n)
    print(f"   LV95 ({e:.2f}, {n:.2f}) -> WGS84 ({lat2:.6f}, {lon2:.6f})")
    print(f"   Roundtrip error: {abs(lat-lat2)*111000:.2f}m lat, {abs(lon-lon2)*111000*math.cos(math.radians(lat)):.2f}m lon")
