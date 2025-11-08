#!/usr/bin/env python3
"""MCP Server for Swiss Height/Elevation (swissALTI3D via GeoAdmin API)."""

import json
import sys
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio

from height_tools import (
    SwissHeightAPI,
    CoordinateTransformer,
    HeightQueryToolkit
)


# Initialize the MCP server
server = Server("geopard-height-tools")

# Initialize tools
height_api = SwissHeightAPI()
transformer = CoordinateTransformer()
toolkit = HeightQueryToolkit()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available height/elevation tools"""
    return [
        Tool(
            name="get_height_at_location",
            description="""Query elevation/height above sea level for a location in Switzerland.

Uses Swiss GeoAdmin API and swissALTI3D digital elevation model (0.5-2m resolution).
Returns height in meters above sea level (m ü. M.) using LHN95 reference.

Supports both WGS84 (GPS) and Swiss LV95 coordinates.

Example use cases:
- "What is the elevation at Bahnhof Luzern?"
- "Height at coordinates 47.05, 8.31"
- "Auf welcher Höhe liegt der Torbogen des Bahnhofs Luzern?"

Returns height with coordinate information and data source details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude in decimal degrees (WGS84). Use with longitude."
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude in decimal degrees (WGS84). Use with latitude."
                    },
                    "easting": {
                        "type": "number",
                        "description": "E coordinate in meters (Swiss LV95). Use with northing."
                    },
                    "northing": {
                        "type": "number",
                        "description": "N coordinate in meters (Swiss LV95). Use with easting."
                    }
                },
                "required": []
            }
        ),
        
        Tool(
            name="get_height_by_name",
            description="""Query elevation for a named location (address, place, landmark).

Combines LocationFinder API with height query to find elevation for:
- Addresses (e.g., "Bahnhofstrasse 1, Luzern")
- Landmarks (e.g., "Bahnhof Luzern", "Torbogen Bahnhof Luzern")
- Place names (e.g., "Gemeinde Luzern", "Pilatus")
- Buildings (EGID, Gebäudeversicherungsnummer)

This is the PREFERRED tool when users ask about height at a named location.

Example: "Auf welcher absoluten Höhe liegt der Torbogen des Bahnhofs Luzern?"
-> Use this tool with location_name="Torbogen Bahnhof Luzern"

Returns location info, coordinates, and elevation in m ü. M.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "Name of location to query (address, landmark, place name, etc.)"
                    }
                },
                "required": ["location_name"]
            }
        ),
        
        Tool(
            name="get_elevation_profile",
            description="""Get elevation profile along a path/route.

Queries elevation at multiple points along a path defined by coordinates.
Useful for:
- Hiking/biking route profiles
- Road gradients
- Terrain cross-sections

Returns elevation profile with min/max heights and elevation difference.

Input: List of coordinates (either WGS84 or LV95)
Output: Profile with ~200 sampled points showing elevation changes""",
            inputSchema={
                "type": "object",
                "properties": {
                    "coordinates": {
                        "type": "array",
                        "description": "List of coordinate pairs [[lat1,lon1], [lat2,lon2], ...] or [[E1,N1], [E2,N2], ...]",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "minItems": 2
                    },
                    "use_wgs84": {
                        "type": "boolean",
                        "description": "If true, coordinates are WGS84 (lat, lon). If false, coordinates are LV95 (E, N). Default: true",
                        "default": True
                    }
                },
                "required": ["coordinates"]
            }
        ),
        
        Tool(
            name="convert_wgs84_to_lv95",
            description="""Convert WGS84 (GPS) coordinates to Swiss LV95 coordinates.

WGS84: Global GPS coordinate system (latitude, longitude in degrees)
LV95: Swiss national coordinate system (easting, northing in meters)

Precision: Better than 1m position accuracy across Switzerland.

Use this when you have GPS coordinates and need Swiss map coordinates.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude in decimal degrees (WGS84)"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude in decimal degrees (WGS84)"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        ),
        
        Tool(
            name="convert_lv95_to_wgs84",
            description="""Convert Swiss LV95 coordinates to WGS84 (GPS) coordinates.

LV95: Swiss national coordinate system (easting, northing in meters)
WGS84: Global GPS coordinate system (latitude, longitude in degrees)

Precision: Better than 1m position accuracy across Switzerland.

Use this when you have Swiss map coordinates and need GPS coordinates.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "easting": {
                        "type": "number",
                        "description": "E coordinate in meters (Swiss LV95)"
                    },
                    "northing": {
                        "type": "number",
                        "description": "N coordinate in meters (Swiss LV95)"
                    }
                },
                "required": ["easting", "northing"]
            }
        ),
        
        Tool(
            name="get_height_with_webmap",
            description="""Query elevation and generate webmap URL showing the location.

Combines height query with map visualization:
1. Gets elevation at location
2. Creates webmap URL zoomed to location with marker
3. Uses 'hoehen' (height/terrain) map theme

Perfect for complete answers that include:
- Elevation value (m ü. M.)
- Interactive map link
- Coordinates in both systems

Use for comprehensive responses to height queries.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "Name of location (address, landmark, etc.). Use with location search."
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude (WGS84). Use with longitude for direct coordinate query."
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude (WGS84). Use with latitude for direct coordinate query."
                    },
                    "easting": {
                        "type": "number",
                        "description": "E coordinate (LV95). Use with northing for direct coordinate query."
                    },
                    "northing": {
                        "type": "number",
                        "description": "N coordinate (LV95). Use with easting for direct coordinate query."
                    },
                    "zoom": {
                        "type": "integer",
                        "description": "Zoom level for webmap (default: 4515)",
                        "default": 4515
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    try:
        if name == "get_height_at_location":
            lat = arguments.get("latitude")
            lon = arguments.get("longitude")
            easting = arguments.get("easting")
            northing = arguments.get("northing")
            
            height_data = height_api.get_height_at_location(
                lat=lat,
                lon=lon,
                easting=easting,
                northing=northing
            )
            
            if height_data:
                result = {
                    "success": True,
                    "height_m": height_data['height_m'],
                    "height_text": f"{height_data['height_m']} m ü. M.",
                    "coordinates_lv95": height_data['coordinates_lv95'],
                    "source": height_data['source'],
                    "height_reference": height_data['height_reference']
                }
                
                # Add WGS84 if available
                if lat is not None and lon is not None:
                    result['coordinates_wgs84'] = {
                        'latitude': lat,
                        'longitude': lon
                    }
            else:
                result = {
                    "success": False,
                    "error": "Could not retrieve height data"
                }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "get_height_by_name":
            location_name = arguments.get("location_name")
            
            result = toolkit.query_height_by_location_name(location_name)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "get_elevation_profile":
            coordinates = arguments.get("coordinates", [])
            use_wgs84 = arguments.get("use_wgs84", True)
            
            # Convert to tuples
            coord_tuples = [tuple(c) for c in coordinates]
            
            profile_data = height_api.get_height_profile(
                coord_tuples,
                use_wgs84=use_wgs84
            )
            
            if profile_data:
                result = {
                    "success": True,
                    "num_points": profile_data['num_points'],
                    "min_height_m": profile_data['min_height_m'],
                    "max_height_m": profile_data['max_height_m'],
                    "height_difference_m": profile_data['height_difference_m'],
                    "source": profile_data['source'],
                    "height_reference": profile_data['height_reference'],
                    # Include full profile data (can be large)
                    "profile_points": profile_data['profile_points'][:50]  # Limit to first 50 for readability
                }
            else:
                result = {
                    "success": False,
                    "error": "Could not retrieve elevation profile"
                }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "convert_wgs84_to_lv95":
            lat = arguments.get("latitude")
            lon = arguments.get("longitude")
            
            easting, northing = transformer.wgs84_to_lv95(lat, lon)
            
            result = {
                "success": True,
                "input_wgs84": {
                    "latitude": lat,
                    "longitude": lon
                },
                "output_lv95": {
                    "easting": round(easting, 2),
                    "northing": round(northing, 2)
                },
                "spatial_reference": "LV95 (EPSG:2056)"
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "convert_lv95_to_wgs84":
            easting = arguments.get("easting")
            northing = arguments.get("northing")
            
            lat, lon = transformer.lv95_to_wgs84(easting, northing)
            
            result = {
                "success": True,
                "input_lv95": {
                    "easting": easting,
                    "northing": northing
                },
                "output_wgs84": {
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6)
                },
                "spatial_reference": "WGS84 (EPSG:4326)"
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "get_height_with_webmap":
            location_name = arguments.get("location_name")
            lat = arguments.get("latitude")
            lon = arguments.get("longitude")
            easting = arguments.get("easting")
            northing = arguments.get("northing")
            zoom = arguments.get("zoom", 4515)
            
            # Get height data
            if location_name:
                height_result = toolkit.query_height_by_location_name(location_name)
                if height_result and height_result.get('success'):
                    easting = height_result['coordinates_lv95']['easting']
                    northing = height_result['coordinates_lv95']['northing']
            else:
                # Query height directly
                if lat is not None and lon is not None:
                    height_result = toolkit.query_height_wgs84(lat, lon)
                    easting = height_result['coordinates_lv95']['easting']
                    northing = height_result['coordinates_lv95']['northing']
                elif easting is not None and northing is not None:
                    height_result = toolkit.query_height_lv95(easting, northing)
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": "Must provide location_name, (latitude, longitude), or (easting, northing)"
                        }, indent=2)
                    )]
            
            # Build webmap URL
            from location_tools import WebmapURLBuilder
            webmap_builder = WebmapURLBuilder()
            
            webmap_url = webmap_builder.build_url(
                map_theme='hoehen',  # Height/terrain map
                x=easting,
                y=northing,
                zoom=zoom,
                add_marker=True
            )
            
            result = {
                "success": height_result.get('success', False),
                "height_m": height_result.get('height_m'),
                "height_text": height_result.get('height_text'),
                "webmap_url": webmap_url,
                "coordinates_lv95": height_result.get('coordinates_lv95'),
                "location_name": height_result.get('location_name'),
                "source": height_result.get('source'),
                "height_reference": height_result.get('height_reference')
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"Unknown tool: {name}"
                }, indent=2)
            )]
    
    except Exception as e:
        import traceback
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "tool": name,
                "traceback": traceback.format_exc()
            }, indent=2)
        )]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
