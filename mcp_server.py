#!/usr/bin/env python3
"""
Geopard MCP Server - Unified Gateway for All Geodata Tools

Provides access to:
- RAG Query System (Level 1-2)
- LocationFinder & Webmaps (Level 3)
- Geodata Services (WMS/WFS/ESRI) (Level 4)
- Dataset Metadata Search
"""

import json
import sys
import os
from typing import Any, Sequence
from pathlib import Path

# Add subdirectories to path
sys.path.insert(0, str(Path(__file__).parent / "location-tools"))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio

# Import location tools
from location_tools import GeopardToolkit

# Import RAG if available
try:
    from rag_query import StateOfTheArtGeopardRAG
    RAG_AVAILABLE = True
except Exception as e:
    RAG_AVAILABLE = False
    print(f"⚠️  RAG not available: {e}", file=sys.stderr)


# Initialize the MCP server
server = Server("geopard-unified")

# Initialize tools
location_toolkit = GeopardToolkit()
rag_system = None

if RAG_AVAILABLE:
    try:
        rag_system = StateOfTheArtGeopardRAG()
        print("✅ RAG system initialized", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  RAG initialization failed: {e}", file=sys.stderr)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Geopard tools"""
    
    tools = [
        # ========== RAG & DATASET SEARCH TOOLS ==========
        Tool(
            name="search_datasets",
            description="""Search for geodata datasets in Canton Luzern using semantic search.
            
This is the primary tool for Level 1-2 queries. Uses state-of-the-art RAG with:
- Azure AI Search semantic ranking (L2 reranker)
- text-embedding-3-large embeddings
- Hybrid search (vector + keyword)
- Inline citations

Returns relevant datasets with:
- Title, MetaUID, data type
- Abstract and purpose
- Keywords and constraints
- Metadata links
- Relevance scores

Use this for questions like:
- "Welcher Datensatz enthält Höhendaten?"
- "Wo finde ich Informationen über Wildruhezonen?"
- "Gibt es Lärmbelastungsdaten?"

**Note:** Requires RAG system to be initialized.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query in German"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of datasets to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    },
                    "use_query_expansion": {
                        "type": "boolean",
                        "description": "Use query expansion for better recall (default: false)",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="ask_about_geodata",
            description="""Ask questions about geodata and get comprehensive answers with citations.
            
This is a complete RAG query that:
1. Searches for relevant datasets
2. Generates a natural language answer
3. Includes inline citations [Quelle N]
4. Provides confidence score
5. Lists all source datasets

Returns:
- Natural language answer in German
- Confidence score (0-100%)
- List of source datasets with links
- Model used

Use this for comprehensive questions like:
- "Wie wurden die Höhendaten erhoben?"
- "Welche Datensätze zeigen Verkehrslärm?"
- "Gibt es Informationen über archäologische Fundstellen?"

**Note:** Requires RAG system to be initialized.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question in natural language (German)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of datasets to retrieve (default: 5)",
                        "default": 5
                    },
                    "use_query_expansion": {
                        "type": "boolean",
                        "description": "Expand query for better recall (default: false)",
                        "default": False
                    }
                },
                "required": ["question"]
            }
        ),
        
        # ========== LOCATION & MAPPING TOOLS ==========
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

Use this when users ask about specific locations or need coordinates for mapping.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Location search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Filter by location type",
                        "enum": ["Adresse", "Gemeinde", "Ortsname", "Flurname", "EGID", "EGRID", "Parzellennummer", "Gebäudeversicherungsnummer"]
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="build_webmap_url",
            description="""Build interactive map URLs for Canton Luzern webmaps.
            
Creates URLs with:
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

Use this to provide users with direct map links to visualize data.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "map_theme": {
                        "type": "string",
                        "description": "Map theme",
                        "enum": ["grundbuchplan", "oberflaechengewaesser", "amtliche_vermessung", "hoehen", "laerm", "default"],
                        "default": "default"
                    },
                    "x": {"type": "number", "description": "X coordinate (Swiss LV95)"},
                    "y": {"type": "number", "description": "Y coordinate (Swiss LV95)"},
                    "zoom": {"type": "integer", "description": "Zoom level (default: 4515)", "default": 4515},
                    "add_marker": {"type": "boolean", "description": "Add marker (default: true)", "default": True}
                },
                "required": []
            }
        ),
        
        Tool(
            name="enrich_dataset_with_location",
            description="""Enrich a dataset result with location-based information.
            
Complete Level 3 enrichment that:
1. Extracts location from user query
2. Gets coordinates via LocationFinder
3. Builds webmap URL with zoom to location
4. Adds Geodatashop links

Returns enriched dataset with:
- webmap_url_with_location: Interactive map URL
- location_coordinates: {x, y}
- location_name: Detected location
- openly_link: Metadata link
- shop_search_link: Download link

Use this to enhance dataset results with spatial context.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "object",
                        "description": "Dataset metadata object"
                    },
                    "user_query": {
                        "type": "string",
                        "description": "User's query (for location extraction)",
                        "default": ""
                    }
                },
                "required": ["dataset"]
            }
        ),
        
        Tool(
            name="extract_location_from_query",
            description="""Extract location information from natural language queries.
            
Attempts to find and geocode location references in user queries.
Returns location info with coordinates and metadata, or null if none found.

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
        ),
        
        # ========== UTILITY TOOLS ==========
        Tool(
            name="get_map_theme_for_dataset",
            description="""Suggest the best map theme for a dataset based on its title.
            
Analyzes dataset title and recommends appropriate webmap theme.
Returns: hoehen, laerm, oberflaechengewaesser, grundbuchplan, or default.

Use this to automatically select the right map visualization.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_title": {
                        "type": "string",
                        "description": "Dataset title to analyze"
                    }
                },
                "required": ["dataset_title"]
            }
        ),
        
        Tool(
            name="build_geodatashop_links",
            description="""Generate download and metadata links for datasets.
            
Creates:
- openly.geo.lu.ch link for metadata (requires metauid)
- geodatenshop.lu.ch search link (uses title/search term)

Use this to provide users with download and metadata access.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "metauid": {"type": "string", "description": "Dataset metadata UID (optional)"},
                    "search_term": {"type": "string", "description": "Search term (optional)"}
                },
                "required": []
            }
        )
    ]
    
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    try:
        # ========== RAG TOOLS ==========
        if name == "search_datasets":
            if not rag_system:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": "RAG system not available. Please check configuration."}, indent=2)
                )]
            
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)
            
            # Perform hybrid search
            results = rag_system.hybrid_search(query, top_k=top_k, use_semantic=True)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "datasets": results
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "ask_about_geodata":
            if not rag_system:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": "RAG system not available. Please check configuration."}, indent=2)
                )]
            
            question = arguments.get("question")
            top_k = arguments.get("top_k", 5)
            use_query_expansion = arguments.get("use_query_expansion", False)
            
            # Complete RAG query
            result = rag_system.query(question, top_k=top_k, use_query_expansion=use_query_expansion)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "result": result
                }, indent=2, ensure_ascii=False)
            )]
        
        # ========== LOCATION TOOLS ==========
        elif name == "search_location":
            query = arguments.get("query")
            limit = arguments.get("limit", 10)
            filter_type = arguments.get("filter_type")
            
            results = location_toolkit.location_finder.search(query, limit=limit, filter_type=filter_type)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "results": results
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "build_webmap_url":
            map_theme = arguments.get("map_theme", "default")
            x = arguments.get("x")
            y = arguments.get("y")
            zoom = arguments.get("zoom", 4515)
            add_marker = arguments.get("add_marker", True)
            
            url = location_toolkit.webmap_builder.build_url(
                map_theme=map_theme, x=x, y=y, zoom=zoom, add_marker=add_marker
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "url": url,
                    "map_theme": map_theme,
                    "coordinates": {"x": x, "y": y} if x and y else None
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "enrich_dataset_with_location":
            dataset = arguments.get("dataset")
            user_query = arguments.get("user_query", "")
            
            enriched = location_toolkit.enrich_dataset_result(dataset, user_query)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "enriched_dataset": enriched
                }, indent=2, ensure_ascii=False)
            )]
        
        elif name == "extract_location_from_query":
            query = arguments.get("query")
            location = location_toolkit.extract_location_from_query(query)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query": query,
                    "location_found": location is not None,
                    "location": location
                }, indent=2, ensure_ascii=False)
            )]
        
        # ========== UTILITY TOOLS ==========
        elif name == "get_map_theme_for_dataset":
            dataset_title = arguments.get("dataset_title")
            theme = location_toolkit.webmap_builder.get_map_for_dataset(dataset_title)
            
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
                result["openly_link"] = location_toolkit.shop_builder.build_openly_link(metauid)
            if search_term:
                result["shop_search_link"] = location_toolkit.shop_builder.build_shop_link(search_term)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Unknown tool: {name}"}, indent=2)
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e), "tool": name}, indent=2)
        )]


async def main():
    """Run the unified MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
