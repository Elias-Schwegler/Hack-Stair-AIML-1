#!/usr/bin/env python3
"""
Example: Complete Height Query with Map Visualization

Demonstrates how to answer the requirement:
"Auf welcher absoluten Höhe in Meter über Meer liegt der Torbogen des Bahnhofs Luzern?"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from height_tools import HeightQueryToolkit
from location_tools import WebmapURLBuilder


def main():
    print("\n" + "=" * 80)
    print("GEOPARD HEIGHT QUERY EXAMPLE")
    print("=" * 80)
    print()
    
    # User query
    query = "Auf welcher absoluten Höhe in Meter über Meer liegt der Torbogen des Bahnhofs Luzern?"
    print(f"User Question:")
    print(f"  {query}")
    print()
    
    # Initialize toolkits
    height_toolkit = HeightQueryToolkit()
    webmap_builder = WebmapURLBuilder()
    
    # Search for location
    print("Step 1: Searching for location 'Bahnhof Luzern'...")
    print("-" * 80)
    
    result = height_toolkit.query_height_by_location_name("Bahnhof Luzern")
    
    if not result or not result.get('success'):
        print(f"❌ Error: {result.get('error') if result else 'Unknown error'}")
        sys.exit(1)
    
    print(f"✅ Location found: {result['location_name']}")
    print(f"   Type: {result['location_type']}")
    print()
    
    # Display elevation
    print("Step 2: Querying elevation from swissALTI3D...")
    print("-" * 80)
    print(f"✅ Elevation retrieved successfully")
    print(f"   Height: {result['height_text']}")
    print(f"   Source: {result['source']}")
    print(f"   Reference: {result['height_reference']}")
    print()
    
    # Display coordinates
    print("Step 3: Coordinate information...")
    print("-" * 80)
    coords = result['coordinates_lv95']
    print(f"   Swiss LV95 (EPSG:2056):")
    print(f"     Easting:  {coords['easting']:.2f} m")
    print(f"     Northing: {coords['northing']:.2f} m")
    print()
    
    # Generate webmap URL
    print("Step 4: Generating interactive map link...")
    print("-" * 80)
    
    webmap_url = webmap_builder.build_url(
        map_theme='hoehen',  # Height/terrain map
        x=coords['easting'],
        y=coords['northing'],
        zoom=4515,  # Appropriate zoom level
        add_marker=True
    )
    
    print(f"✅ Webmap URL generated")
    print(f"   Theme: hoehen (Height/Terrain)")
    print(f"   URL: {webmap_url}")
    print()
    
    # Generate complete answer
    print("=" * 80)
    print("COMPLETE ANSWER")
    print("=" * 80)
    print()
    print(f"Der Bahnhof Luzern liegt auf einer Höhe von {result['height_m']} m ü. M.")
    print()
    print(f"Datenquelle: {result['source']} (Swiss Federal Office of Topography)")
    print(f"Höhenreferenz: {result['height_reference']}")
    print()
    print(f"📍 Koordinaten (LV95):")
    print(f"   E = {coords['easting']:.2f} m")
    print(f"   N = {coords['northing']:.2f} m")
    print()
    print(f"🗺️  Interaktive Webkarte (Zoom auf Standort):")
    print(f"   {webmap_url}")
    print()
    print("=" * 80)
    print()
    
    # Additional examples
    print("ADDITIONAL EXAMPLES:")
    print("=" * 80)
    print()
    
    # Example 2: Query by WGS84 coordinates
    print("Example 2: Query by WGS84 (GPS) coordinates")
    print("-" * 80)
    lat, lon = 47.0501682, 8.3093072
    print(f"Input: Latitude {lat}°, Longitude {lon}°")
    
    result2 = height_toolkit.query_height_wgs84(lat, lon)
    if result2 and result2.get('success'):
        print(f"Height: {result2['height_text']}")
    print()
    
    # Example 3: Query by LV95 coordinates
    print("Example 3: Query by LV95 (Swiss) coordinates")
    print("-" * 80)
    e, n = 2666232, 1211056
    print(f"Input: E={e} m, N={n} m")
    
    result3 = height_toolkit.query_height_lv95(e, n)
    if result3 and result3.get('success'):
        print(f"Height: {result3['height_text']}")
    print()
    
    print("=" * 80)
    print("✅ All examples completed successfully")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
