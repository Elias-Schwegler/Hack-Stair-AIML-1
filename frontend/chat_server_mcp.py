#!/usr/bin/env python3
"""
FastAPI Chat Server with MCP Integration (Best Practices 2025)

Architecture:
- FastAPI for HTTP API
- MCP Server for tool access (RAG, Location Finder, Maps)
- Azure OpenAI for LLM with function calling
- Streaming support for real-time responses

Best Practices:
1. Tool-based architecture (MCP tools as OpenAI functions)
2. Streaming responses for better UX
3. Conversation history management
4. Error handling and fallbacks
5. Health checks and monitoring
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import MCP and RAG modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "backend"))
sys.path.insert(0, str(parent_dir / "location-tools"))

from openai import AzureOpenAI

app = FastAPI(
    title="Kanton Luzern Geodaten Chat",
    description="AI-powered geodata assistant with MCP integration",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Data Models
# =============================================================================

class ChatMessage(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []

class HealthCheck(BaseModel):
    status: str
    rag_available: bool
    mcp_available: bool
    height_tools_available: bool
    azure_openai: bool
    azure_search: bool

# =============================================================================
# MCP Tool Integration
# =============================================================================

# Import MCP tools
MCP_AVAILABLE = False
HEIGHT_TOOLS_AVAILABLE = False

try:
    from location_tools import GeopardToolkit
    location_toolkit = GeopardToolkit()
    MCP_AVAILABLE = True
    print("✓ MCP Location Tools loaded")
except Exception as e:
    print(f"⚠ MCP Location Tools not available: {e}")

try:
    from height_tools import HeightQueryToolkit
    height_toolkit = HeightQueryToolkit()
    HEIGHT_TOOLS_AVAILABLE = True
    print("✓ Height/Elevation Tools loaded")
except Exception as e:
    print(f"⚠ Height Tools not available: {e}")

# Import RAG system
RAG_AVAILABLE = False
rag_system = None

try:
    from rag_query import StateOfTheArtGeopardRAG
    rag_system = StateOfTheArtGeopardRAG()
    RAG_AVAILABLE = True
    print("✓ RAG system loaded successfully")
except Exception as e:
    print(f"⚠ RAG system not available: {e}")

# Initialize Azure OpenAI client
try:
    openai_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    OPENAI_AVAILABLE = True
    print("✓ Azure OpenAI client initialized")
except Exception as e:
    OPENAI_AVAILABLE = False
    print(f"⚠ Azure OpenAI not available: {e}")

# =============================================================================
# MCP Tool Definitions (OpenAI Function Format)
# =============================================================================

def get_mcp_tools_as_openai_functions() -> List[Dict]:
    """
    Convert MCP tools to OpenAI function calling format
    
    Best Practice: Use tools instead of deprecated function calling
    """
    tools = []
    
    if RAG_AVAILABLE:
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "search_geodata_datasets",
                    "description": """Search for geodata datasets in Canton Luzern using semantic search.
                    
Returns relevant datasets with metadata, keywords, and links. Use this for questions about available datasets, data types, or specific geodata.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query in natural language (German)"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ask_geodata_question",
                    "description": """Ask a comprehensive question about geodata and get an AI-generated answer with citations.
                    
Use this for complex questions that require understanding and synthesis of multiple datasets.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Question in natural language (German)"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of datasets to consider (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["question"]
                    }
                }
            }
        ])
    
    if MCP_AVAILABLE:
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "search_location",
                    "description": """Find locations in Canton Luzern and get coordinates.
                    
Supports addresses, place names, building IDs (EGID), and parcel IDs (EGRID).""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Location search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_map_link",
                    "description": """Generate an interactive map URL with optional location marker.
                    
Use this to provide users with visual representation of geodata or locations.""",
                    "parameters": {
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
                            "zoom": {"type": "integer", "description": "Zoom level", "default": 4515}
                        },
                        "required": []
                    }
                }
            }
        ])
    
    if HEIGHT_TOOLS_AVAILABLE:
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "get_height_by_name",
                    "description": """Query elevation/height above sea level for a named location.
                    
Use for questions like 'Wie hoch liegt...', 'Auf welcher Höhe...', 'Elevation of...'.
Returns height in meters above sea level (m ü. M.) using swissALTI3D data.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location_name": {
                                "type": "string",
                                "description": "Location name (address, landmark, place)"
                            }
                        },
                        "required": ["location_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_height_at_coordinates",
                    "description": """Query elevation at specific coordinates (WGS84 or LV95).
                    
Use when you have exact coordinates and need elevation data.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number", "description": "Latitude (WGS84)"},
                            "longitude": {"type": "number", "description": "Longitude (WGS84)"},
                            "easting": {"type": "number", "description": "E coordinate (LV95)"},
                            "northing": {"type": "number", "description": "N coordinate (LV95)"}
                        },
                        "required": []
                    }
                }
            }
        ])
    
    return tools

# =============================================================================
# MCP Tool Execution
# =============================================================================

async def execute_mcp_tool(tool_name: str, arguments: Dict) -> Dict:
    """
    Execute MCP tool and return results
    
    Best Practice: Async execution for better performance
    """
    try:
        if tool_name == "search_geodata_datasets":
            if not RAG_AVAILABLE:
                return {"error": "RAG system not available"}
            
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)
            
            results = rag_system.hybrid_search(query, top_k=top_k, use_semantic=True)
            
            return {
                "success": True,
                "query": query,
                "count": len(results),
                "datasets": results
            }
        
        elif tool_name == "ask_geodata_question":
            if not RAG_AVAILABLE:
                return {"error": "RAG system not available"}
            
            question = arguments.get("question")
            top_k = arguments.get("top_k", 5)
            
            result = rag_system.query(question, top_k=top_k, use_query_expansion=False)
            
            # Extract WMS/WFS URLs from sources
            import re
            wms_urls = []
            wfs_urls = []
            
            # Get raw results to extract service URLs
            raw_results = rag_system.hybrid_search(question, top_k=top_k, use_semantic=True)
            for raw_result in raw_results:
                raw_content = raw_result.get('content', '')
                if 'WMSServer' in raw_content:
                    matches = re.findall(r'https://[^\s"\'\'\}]+/WMSServer[^\s"\'\'\}]*', raw_content)
                    wms_urls.extend(matches)
                if 'WFSServer' in raw_content:
                    matches = re.findall(r'https://[^\s"\'\'\}]+/WFSServer[^\s"\'\'\}]*', raw_content)
                    wfs_urls.extend(matches)
            
            # Remove duplicates and limit
            wms_urls = list(set(wms_urls))[:3]
            wfs_urls = list(set(wfs_urls))[:3]
            
            # Return the RAG answer directly - it's already formatted perfectly
            # No need for the chat LLM to reformulate it
            return {
                "success": True,
                "answer": result["answer"],
                "confidence": result["confidence"],
                "sources": result["sources"],
                "model": result["model"],
                "wms_urls": wms_urls,
                "wfs_urls": wfs_urls
            }
        
        elif tool_name == "search_location":
            if not MCP_AVAILABLE:
                return {"error": "Location tools not available"}
            
            query = arguments.get("query")
            limit = arguments.get("limit", 10)
            
            results = location_toolkit.location_finder.search(query, limit=limit)
            
            return {
                "success": True,
                "query": query,
                "count": len(results),
                "locations": results
            }
        
        elif tool_name == "create_map_link":
            if not MCP_AVAILABLE:
                return {"error": "Map tools not available"}
            
            map_theme = arguments.get("map_theme", "default")
            x = arguments.get("x")
            y = arguments.get("y")
            zoom = arguments.get("zoom", 4515)
            
            url = location_toolkit.webmap_builder.build_url(
                map_theme=map_theme, x=x, y=y, zoom=zoom, add_marker=bool(x and y)
            )
            
            return {
                "success": True,
                "url": url,
                "map_theme": map_theme
            }
        
        elif tool_name == "get_height_by_name":
            if not HEIGHT_TOOLS_AVAILABLE:
                return {"error": "Height tools not available"}
            
            location_name = arguments.get("location_name")
            result = height_toolkit.query_height_by_location_name(location_name)
            
            # Add map URL with zoom to location if coordinates available
            if result.get("success") and "coordinates" in result:
                coords = result["coordinates"]
                if "lv95" in coords:
                    x = coords["lv95"]["easting"]
                    y = coords["lv95"]["northing"]
                    
                    # Generate map URL with zoom
                    map_url = location_toolkit.webmap_builder.build_url(
                        map_theme="hoehen",  # Use height/elevation map theme
                        x=x,
                        y=y,
                        zoom=8000,  # Closer zoom for detailed view
                        add_marker=True
                    )
                    result["map_url"] = map_url
                    result["map_zoom_applied"] = True
            
            return result
        
        elif tool_name == "get_height_at_coordinates":
            if not HEIGHT_TOOLS_AVAILABLE:
                return {"error": "Height tools not available"}
            
            lat = arguments.get("latitude")
            lon = arguments.get("longitude")
            easting = arguments.get("easting")
            northing = arguments.get("northing")
            
            if lat and lon:
                result = height_toolkit.query_height_wgs84(lat, lon)
            elif easting and northing:
                result = height_toolkit.query_height_lv95(easting, northing)
            else:
                return {"error": "Must provide either (latitude, longitude) or (easting, northing)"}
            
            return result
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        return {"error": str(e), "tool": tool_name}

# =============================================================================
# Chat Processing with Function Calling
# =============================================================================

async def process_chat_with_mcp(
    message: str,
    conversation_history: List[Dict[str, str]] = None
) -> Dict:
    """
    Process chat message using Azure OpenAI with MCP tool integration
    
    Best Practice 2025:
    - Use tools (not deprecated functions)
    - Multi-turn conversation support
    - Automatic tool chaining
    """
    if not OPENAI_AVAILABLE:
        return {
            "response": "Azure OpenAI nicht verfügbar. Bitte prüfen Sie die Konfiguration.",
            "error": True
        }
    
    # Build conversation messages
    messages = [
        {
            "role": "system",
            "content": """Geodaten-Assistent für Kanton Luzern. Antworte auf Schweizer Hochdeutsch.

**TOOLS:**
1. **ask_geodata_question**: Geodaten-Fragen → fertige Antworten mit Links (1:1 weitergeben!)
2. **search_location**: "Wo ist..." → Adressen/Orte finden
3. **get_height_by_name**: Höhenabfragen → m ü. M. (swissALTI3D)
4. **create_map_link**: Karten-URLs generieren

**WICHTIG:**
- Geodaten-Fragen → ask_geodata_question (bevorzugt)
- Höhenfragen → get_height_by_name + ask_geodata_question (für Geodatensätze!)
- NIEMALS "Karte aktualisiert" schreiben (passiert automatisch)

**HÖHENABFRAGEN:**
Bei unvollständiger Adresse (z.B. "Rösslimatte 50"):
- Nimm Luzern Stadt (6005) an
- ERSTE ZEILE: "Ich zeige die Höhe für [Adresse] in Luzern. Falls andere Gemeinde gemeint, bitte angeben."
- Rufe get_height_by_name + ask_geodata_question("Höhendaten") auf
- Zeige Höhe UND Geodatensätze mit WMS/WFS-Links
"""
        }
    ]
    
    # Add conversation history
    if conversation_history:
        messages.extend(conversation_history[-6:])  # Last 3 exchanges
    
    # Add current message
    messages.append({
        "role": "user",
        "content": message
    })
    
    # Get available tools
    tools = get_mcp_tools_as_openai_functions()
    
    if not tools:
        # Fallback: No tools available
        return {
            "response": "Die Geodaten-Werkzeuge sind derzeit nicht verfügbar. Bitte prüfen Sie die System-Konfiguration.",
            "error": True
        }
    
    # Call OpenAI with tools (max 10 iterations for tool chaining)
    max_iterations = 10
    iteration = 0
    tool_calls_made = []
    
    while iteration < max_iterations:
        iteration += 1
        
        try:
            response = openai_client.chat.completions.create(
                model=os.getenv("CHAT_MODEL", "gpt-4o"),
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=4000
            )
            
            assistant_message = response.choices[0].message
            
            # Check if model wants to call tools
            if assistant_message.tool_calls:
                # Add assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🔧 Executing tool: {function_name}")
                    print(f"   Arguments: {function_args}")
                    
                    # Track tool calls
                    tool_calls_made.append(function_name)
                    
                    # Execute MCP tool
                    tool_result = await execute_mcp_tool(function_name, function_args)
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                
                # Continue loop to get final response
                continue
            
            else:
                # No more tool calls - return final response
                final_response = assistant_message.content or "Entschuldigung, ich konnte keine Antwort generieren."
                
                # Collect WMS/WFS URLs and location data from all tool results
                all_wms_urls = []
                all_wfs_urls = []
                location_data = None
                map_url = None
                
                for msg in messages:
                    if msg.get("role") == "tool":
                        try:
                            tool_result = json.loads(msg["content"])
                            all_wms_urls.extend(tool_result.get("wms_urls", []))
                            all_wfs_urls.extend(tool_result.get("wfs_urls", []))
                            
                            # Extract location data from search_location results
                            if tool_result.get("locations") and len(tool_result["locations"]) > 0:
                                loc = tool_result["locations"][0]
                                location_data = {
                                    "x": loc.get("cx"),
                                    "y": loc.get("cy"),
                                    "name": loc.get("name"),
                                    "type": loc.get("type"),
                                    "zoom": 16
                                }
                            
                            # Extract location data from height queries (get_height_by_name)
                            if tool_result.get("success") and tool_result.get("coordinates"):
                                coords = tool_result["coordinates"]
                                if "lv95" in coords:
                                    location_data = {
                                        "x": coords["lv95"]["easting"],
                                        "y": coords["lv95"]["northing"],
                                        "name": tool_result.get("location_name", "Standort"),
                                        "type": "height_query",
                                        "zoom": 8000  # Closer zoom for height queries
                                    }
                                    map_url = tool_result.get("map_url")
                        except:
                            pass
                
                result = {
                    "response": final_response,
                    "error": False,
                    "tool_calls_made": tool_calls_made,
                    "iterations": iteration,
                    "wms_urls": list(set(all_wms_urls)),
                    "wfs_urls": list(set(all_wfs_urls))
                }
                
                # Add location data if available
                if location_data:
                    result["location_data"] = location_data
                
                # Add map URL if available (for height queries)
                if map_url:
                    result["map_url"] = map_url
                
                return result
        
        except Exception as e:
            print(f"❌ Error in chat processing: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "response": f"Es gab einen Fehler bei der Verarbeitung: {str(e)}",
                "error": True
            }
    
    # Max iterations reached - should rarely happen with 10 iterations
    return {
        "response": f"Die Anfrage benötigte mehr als {max_iterations} Tool-Aufrufe. Das System hat sein Limit erreicht. Bitte versuchen Sie, die Frage in Teilfragen aufzuteilen oder anders zu formulieren.",
        "error": False,
        "iterations": max_iterations
    }

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health_check() -> HealthCheck:
    """
    Health check endpoint to verify all systems
    """
    return HealthCheck(
        status="healthy" if (RAG_AVAILABLE and OPENAI_AVAILABLE) else "degraded",
        rag_available=RAG_AVAILABLE,
        mcp_available=MCP_AVAILABLE,
        height_tools_available=HEIGHT_TOOLS_AVAILABLE,
        azure_openai=OPENAI_AVAILABLE,
        azure_search=RAG_AVAILABLE  # RAG implies search is working
    )

@app.post("/chat")
async def chat_endpoint(msg: ChatMessage):
    """
    Chat endpoint with MCP integration
    """
    try:
        # Synchronous response
        result = await process_chat_with_mcp(msg.message, msg.conversation_history)
        
        response_data = {
            "response": result["response"],
            "error": result.get("error", False),
            "iterations": result.get("iterations", 0),
            "wms_urls": result.get("wms_urls", []),
            "wfs_urls": result.get("wfs_urls", [])
        }
        
        # Add location_data if available
        if "location_data" in result:
            response_data["location_data"] = result["location_data"]
        
        # Add map_url if available
        if "map_url" in result:
            response_data["map_url"] = result["map_url"]
        
        return JSONResponse(response_data)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Static File Serving
# =============================================================================

@app.get("/{file_path:path}")
async def serve_static(file_path: str):
    """
    Serve static files from the frontend directory
    """
    if not file_path or file_path == "/":
        file_path = "index.html"
    
    file_location = Path(__file__).parent / file_path
    
    if file_location.exists() and file_location.is_file():
        return FileResponse(file_location)
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/")
async def read_root():
    """
    Serve the main index.html page
    """
    return FileResponse(Path(__file__).parent / "index.html")

# =============================================================================
# Server Startup
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🌍 Kanton Luzern Geodaten Chat Server (MCP-Enabled)")
    print("="*70)
    print(f"📍 Server:          http://localhost:8000")
    print(f"💬 Chat interface:  http://localhost:8000")
    print(f"📚 API docs:        http://localhost:8000/docs")
    print(f"🏥 Health check:    http://localhost:8000/health")
    print("─"*70)
    print(f"🗄️  RAG System:      {'✓ Enabled' if RAG_AVAILABLE else '✗ Disabled'}")
    print(f"🔧 MCP Tools:       {'✓ Enabled' if MCP_AVAILABLE else '✗ Disabled'}")
    print(f"⛰️  Height Tools:    {'✓ Enabled' if HEIGHT_TOOLS_AVAILABLE else '✗ Disabled'}")
    print(f"🤖 Azure OpenAI:    {'✓ Connected' if OPENAI_AVAILABLE else '✗ Not connected'}")
    print("─"*70)
    print("⏹️  Press Ctrl+C to stop")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
