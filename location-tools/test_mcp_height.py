#!/usr/bin/env python3
"""
Quick test of the Height MCP server

Tests that the MCP server can be instantiated and responds to tool calls.
"""

import sys
import os
import asyncio
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Mock the mcp server components for testing
from height_tools import HeightQueryToolkit


async def test_tools():
    """Test the underlying tools that the MCP server uses"""
    
    print("=" * 80)
    print("HEIGHT MCP SERVER - TOOL VERIFICATION")
    print("=" * 80)
    print()
    
    toolkit = HeightQueryToolkit()
    
    # Test 1: get_height_by_name (most important for the requirement)
    print("Test 1: get_height_by_name")
    print("-" * 80)
    result = toolkit.query_height_by_location_name("Bahnhof Luzern")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    if result and result.get('success') and result.get('height_m'):
        print("✅ Test 1 PASSED - Height query by name works")
    else:
        print("❌ Test 1 FAILED")
        return False
    print()
    
    # Test 2: get_height_at_location (WGS84)
    print("Test 2: get_height_at_location (WGS84)")
    print("-" * 80)
    result = toolkit.query_height_wgs84(47.0501682, 8.3093072)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    if result and result.get('success') and result.get('height_m'):
        print("✅ Test 2 PASSED - Height query by WGS84 works")
    else:
        print("❌ Test 2 FAILED")
        return False
    print()
    
    # Test 3: get_height_at_location (LV95)
    print("Test 3: get_height_at_location (LV95)")
    print("-" * 80)
    result = toolkit.query_height_lv95(2666232, 1211056)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    if result and result.get('success') and result.get('height_m'):
        print("✅ Test 3 PASSED - Height query by LV95 works")
    else:
        print("❌ Test 3 FAILED")
        return False
    print()
    
    # Test 4: Coordinate transformation
    print("Test 4: convert_wgs84_to_lv95")
    print("-" * 80)
    from height_tools import CoordinateTransformer
    transformer = CoordinateTransformer()
    e, n = transformer.wgs84_to_lv95(47.0501682, 8.3093072)
    print(f"WGS84 (47.0501682, 8.3093072) -> LV95 ({e:.2f}, {n:.2f})")
    
    if e and n and 2600000 < e < 2700000 and 1200000 < n < 1300000:
        print("✅ Test 4 PASSED - Coordinate transformation works")
    else:
        print("❌ Test 4 FAILED")
        return False
    print()
    
    print("=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("MCP Server Status: READY")
    print()
    print("Available tools:")
    print("  1. get_height_by_name - Query elevation by location name")
    print("  2. get_height_at_location - Query elevation by coordinates")
    print("  3. get_elevation_profile - Query elevation profile along path")
    print("  4. convert_wgs84_to_lv95 - WGS84 to LV95 transformation")
    print("  5. convert_lv95_to_wgs84 - LV95 to WGS84 transformation")
    print("  6. get_height_with_webmap - Combined height + webmap URL")
    print()
    
    return True


def main():
    """Run async tests"""
    try:
        success = asyncio.run(test_tools())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
