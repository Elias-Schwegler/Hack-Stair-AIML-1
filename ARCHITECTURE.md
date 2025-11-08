# Geopard System Architecture

> Technical architecture and design documentation for the Geopard AI-powered geodata assistant.

## System Overview

Geopard is built on a modular architecture that combines RAG (Retrieval-Augmented Generation), location services, and interactive mapping through a unified MCP (Model Context Protocol) interface.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Interface Layer                       │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐  ┌──────────────┐         │
│  │   Claude     │    │  Web Browser │  │   Terminal   │         │
│  │   Desktop    │    │   (Chat UI)  │  │     CLI      │         │
│  └──────┬───────┘    └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │ MCP Protocol     │ HTTP/JSON        │ MCP Protocol
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────────┐
│                  Application Layer                              │
│                                                                 │
│  ┌───────────────────────┐    ┌──────────────────────────┐    │
│  │  MCP Server           │    │  Web Server              │    │
│  │  (mcp_server.py)      │    │  (chat_server_mcp.py)    │    │
│  │                       │    │                          │    │
│  │  • CLI interface      │    │  • FastAPI               │    │
│  │  • Claude Desktop     │    │  • Function calling      │    │
│  │  • 8 MCP tools        │    │  • Conversation history  │    │
│  └───────────┬───────────┘    └───────────┬──────────────┘    │
│              │                            │                    │
│              └────────────┬───────────────┘                    │
│                           │                                    │
│  ┌────────────────────────▼─────────────────────────────────┐ │
│  │              Tool Orchestration Layer                     │ │
│  │                                                           │ │
│  │  8 MCP Tools:                                            │ │
│  │  • search_datasets          - Semantic dataset search    │ │
│  │  • ask_about_geodata        - Q&A with citations         │ │
│  │  • search_location          - Geocoding                  │ │
│  │  • build_webmap_url         - Interactive maps           │ │
│  │  • extract_location         - NLP extraction             │ │
│  │  • enrich_dataset           - Spatial enrichment         │ │
│  │  • get_map_theme            - Visualization hints        │ │
│  │  • build_shop_links         - Download/metadata URLs     │ │
│  └───────────────────────┬───────────────────────────────────┘ │
└──────────────────────────┼─────────────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
┌────────▼──────────┐             ┌──────────▼─────────────┐
│   RAG Component   │             │  Location Component    │
│   (backend/)      │             │  (location-tools/)     │
│                   │             │                        │
│ • StateOfTheArt   │             │ • GeopardToolkit       │
│   GeopardRAG      │             │ • LocationFinder       │
│ • Semantic search │             │ • WebmapURLBuilder     │
│ • L2 reranking    │             │ • GeodatashopLinks     │
│ • Embeddings      │             │ • Smart extraction     │
│   cache           │             │                        │
└────────┬──────────┘             └──────────┬─────────────┘
         │                                   │
┌────────▼───────────────────────────────────▼─────────────┐
│                  External Services                       │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Azure AI     │  │ LocationFind │  │   Webmap     │   │
│  │   Search     │  │     API      │  │   Services   │   │
│  │              │  │              │  │              │   │
│  │ • Semantic   │  │ • Geocoding  │  │ • Interactive│   │
│  │   ranking    │  │ • Address    │  │   maps       │   │
│  │ • Vector DB  │  │   search     │  │ • Zoom/focus │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Geodata     │  │    ÖREB      │                     │
│  │   Shop       │  │  (Planned)   │                     │
│  └──────────────┘  └──────────────┘                     │
└───────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Server (`mcp_server.py`)

**Purpose**: Unified entry point for all Geopard tools via Model Context Protocol.

**Features**:
- Single unified interface for CLI and Claude Desktop
- 8 tools across 3 categories (RAG, Location, Utilities)
- Handles tool routing and coordination
- Error handling and validation
- Stateless design for easy scaling

**Tool Categories**:

| Category | Tools | Level |
|----------|-------|-------|
| **RAG & Search** | search_datasets, ask_about_geodata | 1-2 |
| **Location & Maps** | search_location, build_webmap_url, extract_location, enrich_dataset | 3 |
| **Utilities** | get_map_theme, build_shop_links | Helper |

**MCP Configuration** (Claude Desktop):
```json
{
  "mcpServers": {
    "geopard": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}
```

### 2. Web Server (`frontend/chat_server_mcp.py`)

**Purpose**: Web-based interface with full MCP integration via OpenAI function calling.

**Technology Stack**:
- **Backend**: FastAPI with async support
- **Frontend**: Vanilla JavaScript + HTML/CSS
- **AI Integration**: Azure OpenAI with function calling
- **Tools**: All 8 MCP tools exposed as OpenAI functions

**Key Features**:
- **Automatic Tool Orchestration**: LLM decides which tools to use
- **Multi-Turn Conversations**: Full conversation history support
- **Tool Chaining**: Up to 3 iterations for complex queries
- **Health Monitoring**: Real-time system status checks
- **CORS Enabled**: Cross-origin resource sharing configured

**Startup Script** (`start_server.sh`):
```bash
./start_server.sh [OPTIONS]

Options:
  --port PORT     Server port (default: 8000)
  --dev           Development mode with auto-reload
  --help          Show help message
```

**Auto-validation**:
1. ✅ Python version check (≥3.8)
2. ✅ Virtual environment setup
3. ✅ Dependencies installation
4. ✅ Environment file validation
5. ✅ Azure connections test
6. ✅ Port availability check

### 3. RAG Component (`backend/`)

**Purpose**: State-of-the-art retrieval-augmented generation for geodata metadata.

**Technology**:
- **Embeddings**: text-embedding-3-large (3072 dimensions)
- **Vector Store**: Azure AI Search
- **Ranking**: L2 semantic reranker
- **LLM**: GPT-4o for answer generation

**Architecture**:
```
User Query → Embedding Generation → Hybrid Search → Semantic Reranking → LLM Answer Generation
                                    (Vector + Text)     (L2 Reranker)      (with Citations)
```

**Features**:
- **Hybrid Search**: Combines vector similarity and keyword matching
- **German Language Analysis**: Optimized for German queries
- **Chunking Strategy**: Main content + abstract chunks for better retrieval
- **Embedding Cache**: Reduces API calls and improves response time
- **Inline Citations**: [Quelle N] references in responses
- **Confidence Scores**: 0-100% reliability indicator

**Performance**:
- Index size: ~500-1000 datasets
- Search latency: ~200-500ms
- Cache hit rate: ~30-40%
- Cold start: ~2-3s
- Warm query: ~500ms-2s

**Index Schema** (15 fields):
```python
{
    "id": "unique_id",
    "metauid": "DTM2024_DS",
    "type": "Datensatz",
    "title": "Digitales Terrainmodell 2024",
    "abstract": "Detailed description...",
    "keywords": ["Höhe", "Terrain", "LiDAR"],
    "content": "Full text content",
    "content_vector": [0.123, -0.456, ...],  # 3072-dim
    "data_type": "Raster",
    "collection_title": "Höhendaten",
    "purpose": "Visualisierung...",
    "resource_maintenance": "Jährlich",
    "distributor_formats": ["GeoTIFF", "XYZ"],
    "urls_openly": "https://...",
    "urls_webapp": "https://..."
}
```

### 4. Location Component (`location-tools/`)

**Purpose**: Spatial intelligence and location-based enrichment.

**Core Capabilities**:
- **Geocoding**: Address → Coordinates via LocationFinder API
- **Map URL Generation**: Interactive webmap links with zoom
- **Location Extraction**: NLP-based location parsing from queries
- **Dataset Enrichment**: Add spatial context to search results

**LocationFinder API Integration**:
```python
# Supported location types:
- Adresse (Strasse + Nummer + PLZ)
- Gemeinde (Municipality)
- Ortsname, Flurname (Place names)
- EGID (Building ID)
- EGRID (Parcel ID)
- Gebäudeversicherungsnummer
- Parzellennummer
```

**Response Format**:
```json
{
  "id": 602788,
  "type": "Adresse",
  "name": "Mürgi 1.1, 6025 Neudorf",
  "cx": 2658045,  "cy": 1225376,  // Center
  "xmin": 2657995, "ymin": 1225326,  // Extent
  "xmax": 2658095, "ymax": 1225426,
  "fields": {
    "plz": "6025", "str": "Mürgi", "hnr": "1.1",
    "ort": "Neudorf", "egid": "502290823",
    "gem": "Beromünster", "bfsnr": "1081"
  }
}
```

**Map Themes**:
| Theme | Use Case |
|-------|----------|
| `hoehen` | Height/terrain data (DTM, DOM) |
| `laerm` | Noise pollution |
| `grundbuchplan` | Cadastral maps |
| `oberflaechengewaesser` | Surface water |
| `amtliche_vermessung` | Official surveying |
| `default` | General purpose |

**Webmap URL Structure**:
```
https://map.geo.lu.ch/{theme}?FOCUS={x}:{y}:{zoom}&marker
Example: https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker
```

## Data Flow Examples

### Example 1: Simple Dataset Search (Level 1-2)

```
User: "Welche Datensätze enthalten Höhendaten?"
  ↓
MCP Server: ask_about_geodata
  ↓
RAG Component: 
  1. Generate embedding (3072-dim vector)
  2. Hybrid search (vector + text matching)
  3. Semantic reranking (L2 reranker)
  4. Generate answer with GPT-4o
  ↓
Response:
  - Coherent answer with inline citations
  - Source datasets with metadata
  - Links to Openly and Geodatashop
  - Confidence score
```

### Example 2: Location-Enhanced Query (Level 3)

```
User: "Auf welcher Höhe liegt der Bahnhof Luzern?"
  ↓
MCP Server: Orchestrates multiple tools
  ↓
Step 1: search_datasets("Höhendaten")
   → RAG Component
   → Returns: [DTM 2024, DOM 2024, ...]
  ↓
Step 2: extract_location_from_query("Bahnhof Luzern")
   → Location Component
   → LocationFinder API
   → Returns: (2666232, 1211056)
  ↓
Step 3: enrich_dataset_with_location(dataset, query)
   → Combines dataset + location
   → Builds webmap URL with zoom
  ↓
Response:
  - Dataset information (DTM 2024)
  - Interactive map: https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker
  - Download link: https://geodatenshop.lu.ch/...
  - Metadata link: https://www.geo.lu.ch/openly/dataset/...
  - Coordinates: (2666232, 1211056)
```

### Example 3: Multi-Tool Analysis (Level 3)

```
User: "Ist die Adresse Mürgi 1, 6025 Neudorf von Verkehrslärm betroffen?"
  ↓
MCP Server: Complex workflow with 4 tools
  ↓
Tool 1: search_location("Mürgi 1, 6025 Neudorf")
   → LocationFinder API
   → Returns: (2658045, 1225376)
  ↓
Tool 2: search_datasets("Verkehrslärm Gebäude")
   → RAG Component
   → Returns: [Strassenlärmkataster 2018, ...]
  ↓
Tool 3: build_webmap_url("laerm", 2658045, 1225376)
   → URL with noise overlay at exact location
  ↓
Tool 4: ask_about_geodata("Lärmbelastung prüfen")
   → Context-aware answer with legal thresholds
  ↓
Response:
  - Yes/No answer with context
  - Relevant noise datasets
  - Interactive noise map centered on address
  - Instructions to access detailed data
  - Legal threshold information
```

## Technology Stack

### Core Technologies
- **Python 3.10+** - Primary language
- **MCP (Model Context Protocol)** - AI assistant integration
- **asyncio** - Asynchronous operations
- **FastAPI** - Web server framework
- **Uvicorn** - ASGI server

### AI & Search
- **Azure OpenAI** - Embeddings + GPT-4o
  - text-embedding-3-large (3072 dimensions)
  - gpt-4o for answer generation
- **Azure AI Search** - Vector database + semantic ranking
  - L2 semantic reranker
  - Hybrid search (vector + BM25)
- **Semantic Kernel** - Tool orchestration (planned)

### APIs & Services
- **LocationFinder API** - Canton Luzern geocoding
- **Webmap Services** - Interactive maps (map.geo.lu.ch)
- **Geodatashop** - Dataset downloads
- **Openly** - Metadata portal

### Python Dependencies
```txt
mcp>=0.1.0                    # MCP protocol
fastapi>=0.104.0              # Web framework
uvicorn>=0.24.0               # ASGI server
requests>=2.31.0              # HTTP client
python-dotenv>=1.0.0          # Environment config
openai>=1.0.0                 # Azure OpenAI
azure-search-documents>=11.4  # Azure Search
pydantic>=2.0.0               # Data validation
```

## Configuration

## Containerization & Deployment (Docker)

### Architektur mit Docker Compose

Das System läuft in zwei separaten Containern:

- **Backend**: Python 3.11-slim, FastAPI/Uvicorn, MCP, RAG, Location-Tools
- **Frontend**: nginx:alpine, statische Auslieferung von `index.html`, JS/CSS

Beide Container sind über ein gemeinsames Docker-Netzwerk verbunden (`geopard-network`).
Die Backend-API ist unter `http://localhost:8000` erreichbar, das Frontend unter `http://localhost:8080`.

### Docker Compose Aufbau

- `docker-compose.yml` definiert beide Services (`backend`, `frontend`), jeweils mit Healthcheck, Restart-Policy und Port-Mapping.
- Die Backend-Umgebung erhält alle nötigen Azure- und Modell-Umgebungsvariablen aus `.env`.
- Die Daten (`./data`) werden als Read-Only Volume ins Backend gemountet.

### Images bauen & starten

```sh
# Images bauen
docker compose build
# Container starten
docker compose up -d
# Logs ansehen
docker compose logs -f
```

### Best Practices

- Images sind "slim" und "alpine" für minimale Größe und schnelle Builds.
- Healthchecks prüfen API und Frontend-Verfügbarkeit.
- Netzwerk "bridge" erlaubt Outbound-Internet für API-Requests (z.B. Azure).
- Trennung von Backend/Frontend erleichtert Updates und Skalierung.

### Zugriff

- Frontend: http://localhost:8080
- Backend-API: http://localhost:8000

### Hinweise

- Die Images müssen nach Code-Änderungen neu gebaut werden (`docker compose build`).
- Die Container können gestoppt und entfernt werden mit `docker compose down`.


### Environment Variables (`.env`)

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
EMBEDDING_MODEL=text-embedding-3-large
CHAT_MODEL=gpt-4o

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=geopard-rag-v2

# Server Configuration (optional)
PORT=8000
LOG_LEVEL=INFO
```

### Web Server Configuration

**Startup Options**:
```bash
./start_server.sh --port 8080 --dev
```

**CORS Settings** (in `chat_server_mcp.py`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```