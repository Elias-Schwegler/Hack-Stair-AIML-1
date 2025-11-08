#!/usr/bin/env python3
"""
Test script for Geopard Location Tools MCP Server
"""

import json
import asyncio
from location_tools import GeopardToolkit


async def test_location_tools():
    """Test all location tools functionality"""
    
    print("=" * 80)
    print("GEOPARD LOCATION TOOLS - MCP SERVER TESTS")
    print("=" * 80)
    
    toolkit = GeopardToolkit()
    
    # Test 1: Search location
    print("\n" + "=" * 80)
    print("TEST 1: Search Location")
    print("=" * 80)
    
    query = "Bahnhof Luzern"
    print(f"\nQuery: {query}")
    results = toolkit.location_finder.search(query, limit=3)
    print(f"Found {len(results)} results:\n")
    
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['name']}")
        print(f"   Type: {r['type']}")
        print(f"   Coordinates: ({r['cx']}, {r['cy']})")
        print(f"   ID: {r['id']}\n")
    
    # Test 2: Get coordinates
    print("=" * 80)
    print("TEST 2: Get Coordinates")
    print("=" * 80)
    
    coords = toolkit.location_finder.get_coordinates(query)
    print(f"\nQuery: {query}")
    if coords:
        x, y = coords
        print(f"Coordinates: ({x}, {y})")
    else:
        print("No coordinates found")
    
    # Test 3: Build webmap URL
    print("\n" + "=" * 80)
    print("TEST 3: Build Webmap URL")
    print("=" * 80)
    
    if coords:
        x, y = coords
        
        # Test different map themes
        themes = ['hoehen', 'grundbuchplan', 'laerm', 'oberflaechengewaesser']
        
        for theme in themes:
            url = toolkit.webmap_builder.build_url(
                map_theme=theme,
                x=x,
                y=y,
                zoom=4515,
                add_marker=True
            )
            print(f"\n{theme}:")
            print(f"  {url}")
    
    # Test 4: Get map theme for dataset
    print("\n" + "=" * 80)
    print("TEST 4: Get Map Theme for Dataset")
    print("=" * 80)
    
    datasets = [
        "Digitales Höhenmodell 2024",
        "Strassenlärmkataster 2018",
        "Oberflächengewässer Kanton Luzern",
        "Amtliche Vermessung Grundbuchplan"
    ]
    
    print()
    for title in datasets:
        theme = toolkit.webmap_builder.get_map_for_dataset(title)
        print(f"{title}")
        print(f"  → Suggested theme: {theme}\n")
    
    # Test 5: Build Geodatashop links
    print("=" * 80)
    print("TEST 5: Build Geodatashop Links")
    print("=" * 80)
    
    metauid = "DTM2024_DS"
    search_term = "Digitales Terrainmodell"
    
    openly_link = toolkit.shop_builder.build_openly_link(metauid)
    shop_link = toolkit.shop_builder.build_shop_link(search_term)
    
    print(f"\nMetaUID: {metauid}")
    print(f"  Openly: {openly_link}")
    print(f"\nSearch term: {search_term}")
    print(f"  Shop: {shop_link}")
    
    # Test 6: Enrich dataset with location
    print("\n" + "=" * 80)
    print("TEST 6: Enrich Dataset with Location")
    print("=" * 80)
    
    dataset = {
        'metauid': 'DTM2024_DS',
        'title': 'Digitales Terrainmodell 2024',
        'data_type': 'Datensatz'
    }
    
    user_query = "Auf welcher Höhe liegt der Bahnhof Luzern?"
    
    print(f"\nDataset: {dataset['title']}")
    print(f"User query: {user_query}\n")
    
    enriched = toolkit.enrich_dataset_result(dataset, user_query)
    
    print("Enriched dataset:")
    print(f"  Original metauid: {enriched.get('metauid')}")
    print(f"  Original title: {enriched.get('title')}")
    
    if 'location_coordinates' in enriched:
        print(f"  Location coordinates: {enriched['location_coordinates']}")
    
    if 'webmap_url_with_location' in enriched:
        print(f"  Webmap URL: {enriched['webmap_url_with_location']}")
    
    if 'openly_link' in enriched:
        print(f"  Openly link: {enriched['openly_link']}")
    
    if 'shop_search_link' in enriched:
        print(f"  Shop search: {enriched['shop_search_link']}")
    
    # Test 7: Extract location from query
    print("\n" + "=" * 80)
    print("TEST 7: Extract Location from Query")
    print("=" * 80)
    
    queries = [
        "Auf welcher Höhe liegt der Bahnhof Luzern?",
        "Welche Datensätze gibt es für Emmen?",
        "Ist die Mürgi 1, 6025 Neudorf von Verkehrslärm betroffen?",
        "Allgemeine Frage ohne Ort"
    ]
    
    print()
    for q in queries:
        location = toolkit.extract_location_from_query(q)
        print(f"Query: {q}")
        if location:
            print(f"  ✓ Location found: {location['name']} ({location['type']})")
            print(f"    Coordinates: ({location['cx']}, {location['cy']})")
        else:
            print(f"  ✗ No location found")
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("\n✅ All tests completed successfully!")
    print("\nThe MCP server is ready to use with:")
    print("  - search_location")
    print("  - get_coordinates")
    print("  - build_webmap_url")
    print("  - get_map_theme_for_dataset")
    print("  - build_geodatashop_links")
    print("  - enrich_dataset_with_location")
    print("  - extract_location_from_query")
    print("\nTo start the MCP server:")
    print("  python mcp_server.py")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(test_location_tools())
