#!/usr/bin/env python3
"""
MCP Server for Geopard Location Tools

Exposes LocationFinder API and Webmap URL generation as MCP tools.
"""

import json
import sys
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio

from location_tools import (
    LocationFinderTool,
    WebmapURLBuilder,
    GeodatashopLinkBuilder,
    GeopardToolkit
)


# Initialize the MCP server
server = Server("geopard-location-tools")

# Initialize tools
location_finder = LocationFinderTool()
webmap_builder = WebmapURLBuilder()
shop_builder = GeodatashopLinkBuilder()
toolkit = GeopardToolkit()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available location tools"""
    return [
        Tool(
            name="search_location",
            description="""Search for locations in Canton Luzern using the LocationFinder API.
            
Converts location queries to Swiss LV95 coordinates. Supports:
- Addresses (e.g., "Bahnhofstrasse 1, 6003 Luzern")
- Place names (Gemeinde, Ortsname, Flurname)
- EGID (Building ID)
- EGRID (Parcel ID)
- Gebäudeversicherungsnummer

Returns location results with coordinates (cx, cy), extent (xmin, ymin, xmax, ymax), and additional fields.

Use this when users ask about specific locations, addresses, or need coordinates for mapping.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Location search query (address, place name, EGID, etc.)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Optional filter for specific location type",
                        "enum": [
                            "Adresse",
                            "Gemeinde",
                            "Ortsname",
                            "Flurname",
                            "EGID",
                            "EGRID",
                            "Parzellennummer",
                            "Gebäudeversicherungsnummer"
                        ]
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="get_coordinates",
            description="""Get coordinates for a location query (simplified version of search_location).
            
Returns only the center coordinates (x, y) for the best matching location.
Returns null if no location found.

Use this when you only need coordinates for a single location.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Location query to get coordinates for"
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="build_webmap_url",
            description="""Build a URL for Luzern Webmaps with focus and marker.
            
Creates interactive map URLs with:
- Zoom to specific coordinates
- Marker at location
- Themed maps (height, noise, water, cadastre, etc.)

Available map themes:
- grundbuchplan: Cadastral maps
- hoehen: Height/terrain data
- laerm: Noise pollution
- oberflaechengewaesser: Surface water
- amtliche_vermessung: Official surveying
- default: General map

Use this to provide users with direct map links to visualize data at specific locations.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "map_theme": {
                        "type": "string",
                        "description": "Map theme to use",
                        "enum": [
                            "grundbuchplan",
                            "oberflaechengewaesser",
                            "amtliche_vermessung",
                            "hoehen",
                            "laerm",
                            "default"
                        ],
                        "default": "default"
                    },
                    "x": {
                        "type": "number",
                        "description": "X coordinate (Swiss LV95)"
                    },
                    "y": {
                        "type": "number",
                        "description": "Y coordinate (Swiss LV95)"
                    },
                    "zoom": {
                        "type": "integer",
                        "description": "Zoom level (higher = more zoomed in, default: 4515)",
                        "default": 4515
                    },
                    "add_marker": {
                        "type": "boolean",
                        "description": "Whether to add a marker at the location (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        
        Tool(
            name="get_map_theme_for_dataset",
            description="""Determine the appropriate map theme based on a dataset title.
            
Analyzes the dataset title to suggest the most relevant webmap theme.
Returns one of: hoehen, laerm, oberflaechengewaesser, grundbuchplan, or default.

Use this to automatically select the right map visualization for a dataset.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_title": {
                        "type": "string",
                        "description": "Title of the dataset to analyze"
                    }
                },
                "required": ["dataset_title"]
            }
        ),
        
        Tool(
            name="build_geodatashop_links",
            description="""Build links to Geodatashop for dataset downloads and metadata.
            
Creates:
- openly.geo.lu.ch link for dataset metadata (requires metauid)
- geodatenshop.lu.ch search link (uses title/search term)

Use this to provide users with download and metadata access links.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "metauid": {
                        "type": "string",
                        "description": "Metadata UID of the dataset (optional)"
                    },
                    "search_term": {
                        "type": "string",
                        "description": "Search term for shop search (optional)"
                    }
                },
                "required": []
            }
        ),
        
        Tool(
            name="enrich_dataset_with_location",
            description="""Enrich a dataset result with location data and URLs.
            
Combines multiple tools to:
1. Extract location from user query
2. Get coordinates via LocationFinder
3. Build webmap URL with zoom to location
4. Add Geodatashop links

Returns enriched dataset with:
- webmap_url_with_location: Interactive map URL
- location_coordinates: {x, y} coordinates
- openly_link: Metadata link
- shop_search_link: Download search link

Use this as a one-stop enrichment for Level 3 responses.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "object",
                        "description": "Dataset metadata object (must have title, optionally metauid, data_type)"
                    },
                    "user_query": {
                        "type": "string",
                        "description": "User's original query (may contain location information)",
                        "default": ""
                    }
                },
                "required": ["dataset"]
            }
        ),
        
        Tool(
            name="extract_location_from_query",
            description="""Extract location information from a user query.
            
Attempts to find and geocode location references in natural language queries.
Returns location info with coordinates and metadata, or null if no location found.

Use this to detect when users ask about specific places.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User query to extract location from"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    try:
        if name == "search_location":
            query = arguments.get("query")
            limit = arguments.get("limit", 10)
            filter_type = arguments.get("filter_type")
            
            results = location_finder.search(query, limit=limit, filter_type=filter_type)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "results": results
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "get_coordinates":
            query = arguments.get("query")
            coords = location_finder.get_coordinates(query)
            
            if coords:
                x, y = coords
                result = {"success": True, "x": x, "y": y, "query": query}
            else:
                result = {"success": False, "x": None, "y": None, "query": query}
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "build_webmap_url":
            map_theme = arguments.get("map_theme", "default")
            x = arguments.get("x")
            y = arguments.get("y")
            zoom = arguments.get("zoom", 4515)
            add_marker = arguments.get("add_marker", True)
            
            url = webmap_builder.build_url(
                map_theme=map_theme,
                x=x,
                y=y,
                zoom=zoom,
                add_marker=add_marker
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "url": url,
                    "map_theme": map_theme,
                    "coordinates": {"x": x, "y": y} if x and y else None,
                    "zoom": zoom
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "get_map_theme_for_dataset":
            dataset_title = arguments.get("dataset_title")
            theme = webmap_builder.get_map_for_dataset(dataset_title)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "dataset_title": dataset_title,
                    "suggested_theme": theme
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "build_geodatashop_links":
            metauid = arguments.get("metauid")
            search_term = arguments.get("search_term")
            
            result = {"success": True}
            
            if metauid:
                result["openly_link"] = shop_builder.build_openly_link(metauid)
            
            if search_term:
                result["shop_search_link"] = shop_builder.build_shop_link(search_term)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "enrich_dataset_with_location":
            dataset = arguments.get("dataset")
            user_query = arguments.get("user_query", "")
            
            enriched = toolkit.enrich_dataset_result(dataset, user_query)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "enriched_dataset": enriched
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "extract_location_from_query":
            query = arguments.get("query")
            location = toolkit.extract_location_from_query(query)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query": query,
                    "location_found": location is not None,
                    "location": location
                }, indent=2, ensure_ascii=False)
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "tool": name
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
