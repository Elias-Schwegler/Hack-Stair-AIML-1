#!/usr/bin/env python3
"""
Test script for height/elevation tools

Tests the height query functionality for Bahnhof Luzern and other locations.
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(__file__))

from height_tools import HeightQueryToolkit, CoordinateTransformer
import math


def test_bahnhof_luzern():
    """Test height query for Bahnhof Luzern (the main requirement)"""
    print("=" * 80)
    print("TEST: Height of Bahnhof Luzern Torbogen")
    print("=" * 80)
    
    toolkit = HeightQueryToolkit()
    
    # Try different search terms
    search_terms = [
        "Bahnhof Luzern",
        "Torbogen Bahnhof Luzern",
        "Luzern Bahnhof"
    ]
    
    for search_term in search_terms:
        print(f"\n🔍 Searching for: '{search_term}'")
        print("-" * 80)
        
        result = toolkit.query_height_by_location_name(search_term)
        
        if result and result.get('success'):
            print(f"✅ SUCCESS")
            print(f"   Location: {result.get('location_name')} ({result.get('location_type')})")
            print(f"   Height: {result.get('height_text')}")
            print(f"   Coordinates LV95:")
            print(f"     E = {result['coordinates_lv95']['easting']:.2f} m")
            print(f"     N = {result['coordinates_lv95']['northing']:.2f} m")
            print(f"   Source: {result.get('source')}")
            print(f"   Reference: {result.get('height_reference')}")
            
            # Expected answer: around 435 m ü. M.
            height = result.get('height_m')
            if height and 430 <= height <= 440:
                print(f"   ✓ Height is in expected range (430-440 m ü. M.)")
            else:
                print(f"   ⚠ Height {height} m is outside expected range (430-440 m ü. M.)")
        else:
            print(f"❌ FAILED")
            print(f"   Error: {result.get('error') if result else 'Unknown error'}")
        
        print()


def test_coordinate_transformations():
    """Test coordinate transformations"""
    print("=" * 80)
    print("TEST: Coordinate Transformations")
    print("=" * 80)
    
    transformer = CoordinateTransformer()
    
    # Test case: Lucerne
    print("\n📍 Test Location: Lucerne")
    print("-" * 80)
    
    # Known coordinates
    wgs84_lat = 47.0501682
    wgs84_lon = 8.3093072
    
    print(f"Input WGS84:")
    print(f"  Latitude:  {wgs84_lat}°")
    print(f"  Longitude: {wgs84_lon}°")
    
    # Transform to LV95
    lv95_e, lv95_n = transformer.wgs84_to_lv95(wgs84_lat, wgs84_lon)
    print(f"\nTransformed to LV95:")
    print(f"  Easting:  {lv95_e:.2f} m")
    print(f"  Northing: {lv95_n:.2f} m")
    
    # Transform back to WGS84
    back_lat, back_lon = transformer.lv95_to_wgs84(lv95_e, lv95_n)
    print(f"\nTransformed back to WGS84:")
    print(f"  Latitude:  {back_lat:.6f}°")
    print(f"  Longitude: {back_lon:.6f}°")
    
    # Calculate error
    lat_error_m = abs(wgs84_lat - back_lat) * 111000
    lon_error_m = abs(wgs84_lon - back_lon) * 111000 * math.cos(math.radians(wgs84_lat))
    print(f"\nRoundtrip Error:")
    print(f"  Latitude:  {lat_error_m:.4f} m")
    print(f"  Longitude: {lon_error_m:.4f} m")
    
    if lat_error_m < 1.0 and lon_error_m < 1.0:
        print("  ✓ Error within expected tolerance (<1m)")
    else:
        print("  ⚠ Error exceeds expected tolerance")
    
    print()


def test_wgs84_height_query():
    """Test height query with WGS84 coordinates"""
    print("=" * 80)
    print("TEST: Height Query with WGS84 Coordinates")
    print("=" * 80)
    
    toolkit = HeightQueryToolkit()
    
    # Lucerne coordinates
    lat = 47.0501682
    lon = 8.3093072
    
    print(f"\n📍 Query height at WGS84 coordinates:")
    print(f"   Latitude:  {lat}°")
    print(f"   Longitude: {lon}°")
    print("-" * 80)
    
    result = toolkit.query_height_wgs84(lat, lon)
    
    if result and result.get('success'):
        print(f"✅ SUCCESS")
        print(f"   Height: {result.get('height_text')}")
        print(f"   Coordinates LV95:")
        print(f"     E = {result['coordinates_lv95']['easting']:.2f} m")
        print(f"     N = {result['coordinates_lv95']['northing']:.2f} m")
        print(f"   Source: {result.get('source')}")
    else:
        print(f"❌ FAILED")
        print(f"   Error: {result.get('error') if result else 'Unknown error'}")
    
    print()


def test_lv95_height_query():
    """Test height query with LV95 coordinates"""
    print("=" * 80)
    print("TEST: Height Query with LV95 Coordinates")
    print("=" * 80)
    
    toolkit = HeightQueryToolkit()
    
    # Lucerne approximate LV95 coordinates
    easting = 2666000
    northing = 1212000
    
    print(f"\n📍 Query height at LV95 coordinates:")
    print(f"   Easting:  {easting} m")
    print(f"   Northing: {northing} m")
    print("-" * 80)
    
    result = toolkit.query_height_lv95(easting, northing)
    
    if result and result.get('success'):
        print(f"✅ SUCCESS")
        print(f"   Height: {result.get('height_text')}")
        print(f"   Source: {result.get('source')}")
    else:
        print(f"❌ FAILED")
        print(f"   Error: {result.get('error') if result else 'Unknown error'}")
    
    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "HEIGHT TOOLS TEST SUITE" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        # Main test: Bahnhof Luzern (the requirement)
        test_bahnhof_luzern()
        
        # Additional tests
        test_coordinate_transformations()
        test_wgs84_height_query()
        test_lv95_height_query()
        
        print("=" * 80)
        print("✅ All tests completed")
        print("=" * 80)
        print()
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
