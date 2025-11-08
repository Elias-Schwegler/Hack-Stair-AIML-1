#!/usr/bin/env python3
"""
FastAPI Chat Server with MCP Integration

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
            
            # Extract URLs from sources and content
            import re
            wms_urls = []
            wfs_urls = []
            download_urls = []
            metadata_urls = []
            
            # Extract from sources (preferred - structured data)
            for source in result.get("sources", []):
                if source.get("webapp_url"):
                    download_urls.append(source["webapp_url"])
                if source.get("openly_url"):
                    metadata_urls.append(source["openly_url"])
            
            # Also extract WMS/WFS from raw search results
            raw_results = rag_system.hybrid_search(question, top_k=top_k, use_semantic=True)
            for raw_result in raw_results:
                raw_content = raw_result.get('content', '')
                if 'WMSServer' in raw_content:
                    matches = re.findall(r'https://[^\s"\'\'\}]+/WMSServer[^\s"\'\'\}]*', raw_content)
                    wms_urls.extend(matches)
                if 'WFSServer' in raw_content:
                    matches = re.findall(r'https://[^\s"\'\'\}]+/WFSServer[^\s"\'\'\}]*', raw_content)
                    wfs_urls.extend(matches)
            
            # Remove duplicates
            wms_urls = list(set(wms_urls))[:3]
            wfs_urls = list(set(wfs_urls))[:3]
            download_urls = list(set(download_urls))[:5]
            metadata_urls = list(set(metadata_urls))[:5]
            
            # Return the RAG answer with all URLs
            return {
                "success": True,
                "answer": result["answer"],
                "confidence": result["confidence"],
                "sources": result["sources"],
                "model": result["model"],
                "wms_urls": wms_urls,
                "wfs_urls": wfs_urls,
                "download_urls": download_urls,
                "metadata_urls": metadata_urls
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
            "content": """
            Du bist ein Geodaten-Assistent für den Kanton Luzern.  
            Antworte konsequent auf **Schweizer Hochdeutsch**.

            Beantworte **nur** Fragen, die sich auf Geodaten, Karten, Standorte, Höhen oder den Kanton Luzern beziehen.  
            Bei Themen ausserhalb dieses Bereichs:
            → Freundlich mitteilen, dass du nur bei Geodaten für den Kanton Luzern unterstützen kannst.
            
            
            **DEINE WERKZEUGE:**
            Du hast Zugriff auf folgende Werkzeuge zur Informationsbeschaffung:

            1. **ask_geodata_question**: Für ALLE Fragen zu Geodatensätzen
               - Nutze dies für Fragen wie "Welcher Datensatz...", "Wo finde ich...", "Wie kann ich..."
               - Das RAG-System liefert detaillierte Antworten mit Quellenangaben
               - Bevorzuge dieses Tool für komplexe Geodaten-Fragen

            2. **search_geodata_datasets**: Für  Suche nach Datensätzen
               - Nutze dies immer, wenn du die Namen/Metadaten der Datensätze brauchst
               - Gibt Liste von Datensätzen ohne ausformulierte Antwort
               - **Bevorzuge ask_geodata_question für bessere Antworten**

            3. **search_location**: Finde Orte und Koordinaten
               - Für Adressen, Ortsnamen, Gebäude-IDs (EGID), Parzellen-IDs (EGRID)
               - **Nutze dies für Fragen wie "Wo ist...", "Zeige mir...", "Wie komme ich zu..."**
               - **Die Karte wird automatisch zum gefundenen Ort zoomen und einen Marker setzen**

            4. **create_map_link**: Erstelle Karten-Links
               - Nach erfolgreicher Ortssuche, um interaktive Karten zu zeigen

            5. **get_height_by_name**: Höhenabfragen → m ü. M. (swissALTI3D)
               - Nutze dies für Fragen wie "Wie hoch liegt...", "Auf welcher Höhe...", "Elevation of..."
               - Liefert die Höhe in Metern über Meer mit Quellenangaben


            **WICHTIGE REGELN:**

            **Tool-Auswahl:**
            - Bei Geodaten-Fragen: Nutze **ask_geodata_question** (nicht search_geodata_datasets)
            - **Bei Ortsfragen: Nutze IMMER search_location für "Wo ist...", "Zeige...", Adressen, etc.**
            - Das ask_geodata_question Tool liefert FERTIGE, detaillierte Antworten mit allen Quellenangaben, Metadaten und Links
            - Deine Aufgabe: **Gib die Antwort DIREKT weiter** ohne sie zu verändern oder umzuformulieren
            - Höhenfragen → get_height_by_name + ask_geodata_question (für Geodatensätze!)
            - NIEMALS "Karte aktualisiert" schreiben (passiert automatisch)

            **Location-Handling:**
            - Bei Fragen nach Standorten, Adressen oder "Wo ist...": **Nutze search_location**
            - Die Karte wird automatisch zum Ort zoomen und einen roten Marker anzeigen
            - Informiere den Benutzer, dass die Karte aktualisiert wurde

            **HÖHENABFRAGEN:**
            Bei unvollständiger Adresse (z.B. "Rösslimatte 50"):
            - Nimm Luzern Stadt (6005) an
            - ERSTE ZEILE: "Ich zeige die Höhe für [Adresse] in Luzern. Falls andere Gemeinde gemeint, bitte angeben."
            - Rufe get_height_by_name + ask_geodata_question("Höhendaten") auf
            - Zeige Höhe UND Geodatensätze mit Download-URL Metadaten-URL - wrzonxxx_col_v1 ist für jeden Datensatz anders)

            **Antwort-Format:**
            - Wenn ask_geodata_question eine Antwort liefert: **Gib sie 1:1 weiter** 
            - Füge KEINE eigenen Interpretationen oder Umformulierungen hinzu
            - **PFLICHT: Füge IMMER folgende Links hinzu:**
              * 📥 **Download**: Nutze `download_urls` aus dem Tool-Result
              * 📋 **Metadaten**: Nutze `metadata_urls` aus dem Tool-Result
              * 🗺️ **Webkarte**: [Karten-Link mit Zoom auf Standort, falls verfügbar]
            - **WICHTIG**: Die URLs sind in den Tool-Results unter `download_urls` und `metadata_urls` verfügbar
            - Extrahiere die URLs aus dem JSON-Result und zeige sie an
            - Sei freundlich und hilfsbereit
            - Antworte auf Schweizer Hochdeutsch

            **WICHTIG: Nutze die Tool-Ergebnisse EXAKT wie geliefert!**
            - ask_geodata_question liefert bereits perfekt formatierte, fachlich korrekte Antworten
            - Übernimm diese Antworten vollständig und unverändert
            - Ändere KEINE Jahreszahlen, Datensatznamen oder technischen Details


            **DETAILLIERTE BEISPIELE:**

            **Beispiel 1: Datensatz-Suche mit Höhenabfrage**
            User: "Welcher Datensatz zeigt mir die absolute Höhe (in Meter über Meer) des Torbogens vor dem Bahnhof Luzern?"
            
            Schritt 1: Rufe ask_geodata_question("Welcher Datensatz zeigt Höhendaten?") auf
            Schritt 2: Rufe search_location("Torbogen Bahnhof Luzern") auf
            
            Antwort:
            "Das **Digitale Terrainmodell (DTM) 2024** zeigt die absoluten Höhen in Meter über Meer. Es bildet die Topografie der Erdoberfläche ohne Bewuchs und Bebauung ab und eignet sich für vielseitige Verwendungen im Bereich der Geowissenschaften und der Technik (Photogrammetrie, Visualisierungen, Bauwesen, Forstwesen, Telekommunikation, Raumplanung, Naturgefahren, Energiebewirtschaftung).
            
            📥 **Download**: https://daten.geo.lu.ch/produkt/dtm24025_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DTM24025_DS&version=1
            🗺️ **Webkarte**: [Link mit Zoom auf Bahnhof Luzern]
            
            Die Daten wurden mittels LiDAR-Befliegung im Jahr 2024 erhoben (Lagegenauigkeit: ±10cm SD, Höhengenauigkeit: ±20cm SD)."

            ---

            **Beispiel 2: Informationen zum Datensatz - Erhebungsmethode**
            User: "Wie wurden die Höhendaten erhoben?"
            
            Schritt 1: Rufe ask_geodata_question("Wie wurden die Höhendaten erhoben?") auf
            
            Antwort:
            "Die Höhendaten wurden mittels **LiDAR-Befliegung im Jahr 2024** erhoben. Das digitale Oberflächenmodell (DOM) 2024 repräsentiert die Erdoberfläche samt aller darauf befindlicher Objekte (inkl. Bewuchs und Bebauung). Die Punktwolke hat eine minimale Punktdichte von 16 Punkten pro m² und wird im Format ASCII und LAS 1.4 abgegeben.
            
            **Technische Details:**
            - Lagegenauigkeit: ±10cm SD
            - Höhengenauigkeit: ±20cm SD
            - Punktdichte: ≥16 Punkte/m²
            - Klassifizierte Punktwolke mit 13 verschiedenen Klassen (Boden, Vegetation, Gebäude, Wasser, etc.)
            
            📥 **Download Punktwolke**: https://daten.geo.lu.ch/produkt/dom24wlk_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DOM24WLK_DS&version=1
            
            📥 **Download DTM-Raster**: https://daten.geo.lu.ch/produkt/dtm24025_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DTM24025_DS&version=1
            
            Weitere Informationen finden Sie im Geoportal."

            ---

            **Beispiel 3: Räumliche Einordnung mit Höhenabfrage**
            User: "Auf welcher absoluten Höhe (in Meter über Meer) liegt der Torbogen des Bahnhofs Luzern?"
            
            Schritt 1: Rufe get_height_by_name("Torbogen Bahnhof Luzern") auf
            Schritt 2: Rufe ask_geodata_question("Höhendaten Kanton Luzern") auf
            
            Antwort:
            "Der Torbogen des Bahnhofs Luzern liegt auf einer Höhe von **435 m ü. M.**
            
            🗺️ **Webkarte**: Die Karte wurde automatisch auf den Standort gezoomt und zeigt die genaue Position.
            
            **Verfügbare Höhendatensätze:**
            
            📥 **Digitales Terrainmodell (DTM) 2024**: https://daten.geo.lu.ch/produkt/dtm24025_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DTM24025_DS&version=1
            
            📥 **Höhenlinien 1m**: https://daten.geo.lu.ch/produkt/dtm24h1m_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DTM24H1M_DS&version=1
            
            Quelle: swissALTI3D Digitales Terrainmodell 2024, erhoben mittels LiDAR-Befliegung"

            ---

            **Beispiel 4: Gebäude-ID (EGID) Abfrage**
            User: "EGID 123456"
            
            Schritt 1: Rufe search_location("EGID 123456") auf
            Schritt 2: Rufe ask_geodata_question("Geodaten für Gebäude EGID 123456") auf
            
            Antwort:
            "Zu diesem Gebäude (EGID 123456) sind folgende Geodaten verfügbar:
            
            **Amtliche Vermessung:**
            Die amtliche Vermessung liefert geometrische Daten zum Grundeigentum. Die Daten sind in drei verschiedenen Modellen verfügbar.
            📥 Download: https://daten.geo.lu.ch/produkt/amtverxx_col_v2
            📋 Metadaten: https://www.geo.lu.ch/meta?metauid=AMTVERXX_COL&version=2
            
            **Gebäude- und Wohnungsregister (GWR):**
            📥 Download: https://daten.geo.lu.ch/produkt/gwr_ds_v1
            📋 Metadaten: https://www.geo.lu.ch/meta?metauid=GWR_DS&version=1
            
            **Höheninformationen:**
            📥 Höhenlinien 1m: https://daten.geo.lu.ch/produkt/dtm24h1m_ds_v1
            📋 Metadaten: https://www.geo.lu.ch/meta?metauid=DTM24H1M_DS&version=1
            
            🗺️ **ÖREB-Kataster**: [Link mit Zoom auf Gebäude]
            
            Die Karte wurde automatisch auf das Gebäude gezoomt."

            ---

            **Beispiel 5: Verkehrslärmbetroffenheit**
            User: "Ist das Gebäude an der Bahnhofstrasse 15 in Luzern von Verkehrslärmbeeinträchtigungen betroffen?"
            
            Schritt 1: Rufe search_location("Bahnhofstrasse 15, Luzern") auf
            Schritt 2: Rufe ask_geodata_question("Verkehrslärm Bahnhofstrasse 15 Luzern") auf
            
            Antwort:
            "Basierend auf den **Strassenlärmkataster 2018** Daten kann ich Ihnen folgende Information geben:
            
            Der Strassenlärmkataster zeigt auf, wie stark einzelne Gebäude entlang der Kantonsstrassen mit Strassenlärm belastet sind. Die Lärmschutzverordnung (LSV) des Bundes schreibt in strassenlärmbelasteten Gebieten die Erstellung von Lärmbelastungskatastern vor. Der Kataster bildet die Grundlage zur Bekämpfung des Lärms und insbesondere zur Planung und Durchführung der erforderlichen Sanierungsmassnahmen.
            
            📥 **Strassenlärmkataster 2018**: https://daten.geo.lu.ch/produkt/slkat18x_col_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=SLKAT18X_COL&version=1
            🗺️ **Webkarte Lärm**: [Link mit Zoom auf Bahnhofstrasse 15]
            
            **Zusätzlich verfügbar:**
            📥 **Lärmempfindlichkeitsstufen**: https://daten.geo.lu.ch/produkt/laemgdmx_ref_v2
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=LAEMGDMX_REF&version=2
            
            Die Karte zeigt die aktuelle Lärmbelastung an diesem Standort. In den kommunalen Zonenplänen sind gebietsweise Empfindlichkeitsstufen festgelegt, um die zulässige Lärmbelastung zu regeln."

            ---

            **Beispiel 6: Statistische Abfrage zu Lärmbelastung**
            User: "Bei wie vielen Gebäuden im Kanton wird der Alarmwert beim Verkehrslärm erreicht bzw. überschritten?"
            
            Schritt 1: Rufe ask_geodata_question("Anzahl Gebäude mit Alarmwert Verkehrslärm Kanton Luzern") auf
            
            Antwort:
            "Basierend auf dem **Strassenlärmkataster 2018** kann ich Ihnen folgende Informationen geben:
            
            [Detaillierte Antwort vom RAG-System mit statistischen Daten zur Lärmbelastung]
            
            Der Strassenlärmkataster zeigt auf, wie stark einzelne Gebäude entlang der Kantonsstrassen mit Strassenlärm belastet sind. Die Lärmschutzverordnung (LSV) des Bundes schreibt in strassenlärmbelasteten Gebieten die Erstellung von Lärmbelastungskatastern vor.
            
            📥 **Strassenlärmkataster herunterladen**: https://daten.geo.lu.ch/produkt/slkat18x_col_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=SLKAT18X_COL&version=1
            🗺️ **Webkarte Lärmkataster**: [Link zur kantonalen Übersichtskarte]
            
            Der Kataster bildet die Grundlage zur Planung und Durchführung der erforderlichen Sanierungsmassnahmen."

            ---

            **Beispiel 7: Analyse - Teuerste Wohnlagen**
            User: "Welches sind die teuersten Wohnlagen im Kanton Luzern?"
            
            Schritt 1: Rufe ask_geodata_question("Teuerste Wohnlagen Kanton Luzern") auf
            
            Antwort:
            "[Detaillierte Antwort vom RAG-System mit Wohnlagen-Daten und Analysen]
            
            📥 **Wohnlagen-Daten**: https://daten.geo.lu.ch/produkt/wohnlagen_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=WOHNLAGEN_DS&version=1
            🗺️ **Webkarte**: [Link zur thematischen Karte]
            
            Weitere statistische Auswertungen und räumliche Analysen können über das Geoportal durchgeführt werden."

            ---

            **Beispiel 8: Hangneigung und Geländeanalyse**
            User: "Wo finde ich Daten zur Hangneigung für Erdrutsch-Analysen?"
            
            Schritt 1: Rufe ask_geodata_question("Hangneigung Erdrutsch Geländeanalyse") auf
            
            Antwort:
            "Für Geländeanalysen und Modellierung von geotechnischen Gefahren wie Erdrutschen, Muren oder Rutschungen steht das **Digitale Terrainmodell (DTM) 2024: Hangneigung** zur Verfügung.
            
            Der Datensatz zeigt die aus dem digitalen Terrainmodell 2024 abgeleitete Hangneigung in Prozent im 1m-Raster. Er eignet sich für vielseitige Verwendungen im Bereich der Geländeanalyse, z.B. für die Bodenkartierung oder zur Modellierung von geotechnischen Gefahren.
            
            📥 **Hangneigung herunterladen**: https://daten.geo.lu.ch/produkt/dtm24hng_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DTM24HNG_DS&version=1
            
            📥 **Basis: DTM 2024**: https://daten.geo.lu.ch/produkt/dtm24025_ds_v1
            📋 **Metadaten**: https://www.geo.lu.ch/meta?metauid=DTM24025_DS&version=1
            
            Die Daten basieren auf der LiDAR-Befliegung 2024 mit einer Höhengenauigkeit von ±20cm SD."


            **LINK-FORMAT (wichtig für korrekte Extraktion):**
            - Download-Links folgen dem Muster: https://daten.geo.lu.ch/produkt/[produkt_id]
            - Metadaten-Links: https://www.geo.lu.ch/meta?metauid=[ID]&version=[X]
            - **Nutze die Informationen aus den Tool-Ergebnissen** (webapp.url und openly.url)
            - Füge IMMER beide Links hinzu, wenn verfügbar
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
                
                # Collect all URLs and location data from tool results
                all_wms_urls = []
                all_wfs_urls = []
                all_download_urls = []
                all_metadata_urls = []
                location_data = None
                map_url = None
                
                for msg in messages:
                    if msg.get("role") == "tool":
                        try:
                            tool_result = json.loads(msg["content"])
                            all_wms_urls.extend(tool_result.get("wms_urls", []))
                            all_wfs_urls.extend(tool_result.get("wfs_urls", []))
                            all_download_urls.extend(tool_result.get("download_urls", []))
                            all_metadata_urls.extend(tool_result.get("metadata_urls", []))
                            
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
                    "wfs_urls": list(set(all_wfs_urls)),
                    "download_urls": list(set(all_download_urls)),
                    "metadata_urls": list(set(all_metadata_urls))
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
            "wfs_urls": result.get("wfs_urls", []),
            "download_urls": result.get("download_urls", []),
            "metadata_urls": result.get("metadata_urls", [])
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
