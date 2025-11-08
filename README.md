# Geopard - AI-Powered Geodata Assistant

> Intelligent chatbot for Canton Luzern's geoportal - making geodata accessible through natural language queries.

## 🎯 Overview

Geopard is an AI-powered assistant that helps users find, understand, and access geodata from Canton Luzern. It combines state-of-the-art RAG (Retrieval-Augmented Generation) with location services and interactive mapping capabilities.

### Key Features

- **🔍 Smart Search** - Semantic search across 500+ geodata datasets
- **💬 Natural Language Q&A** - Ask questions in German, get precise answers with citations
- **📍 Location Intelligence** - Find places, coordinates, and spatial context
- **🗺️ Interactive Maps** - Generate direct links to webmaps with zoom and markers
- **🌐 Web Interface** - User-friendly chat interface with map integration

### Capability Levels

| Level | Capability | Status |
|-------|-----------|--------|
| **Level 1** | Dataset Search | ✅ Complete |
| **Level 2** | Metadata Q&A | ✅ Complete |
| **Level 3** | Spatial Context & Maps | ✅ Complete |
| **Level 4** | Direct Data Access & Analysis | 🚧 Planned |

## 🚀 Quick Start

### Option 1: Docker (Recommended)

This repository includes a `docker-compose.yml` that builds two services:

- `backend` (FastAPI + Uvicorn) exposed on port 8000
- `frontend` (nginx static server) exposed on port 8080

**Prerequisites:** Docker (Desktop) and Compose plugin

1) Make sure your `.env` is present at the repo root (it will be read by Compose). If you don't have one, copy the example and fill credentials:

```powershell
cp .env.example .env
# edit .env with your Azure keys
notepad .env
```

2) Build images and start services (from repo root):

```powershell
docker compose build
docker compose up -d
```

3) Follow logs (optional):

```powershell
docker compose logs -f
```

4) Access the services in your browser:

- Frontend UI: http://localhost:8080
- Backend API: http://localhost:8000 (e.g. /docs or /health)

5) Stop and remove containers:

```powershell
docker compose down --remove-orphans
```

Notes & tips:
- Compose automatically reads `.env` in the repo root; ensure your secrets are set there (do NOT commit secrets).
- Use `docker compose ps` to check service status.
- If you run into port conflicts, stop the conflicting process or change ports in `docker-compose.yml`.
- The containers have outbound network access by default (bridge network), so Azure requests should work from inside the container.

👉 **See [DOCKER.md](DOCKER.md) for additional platform-specific instructions and troubleshooting**

### Option 2: Native Python Setup

**Prerequisites:** Python 3.10+, Azure OpenAI & Search access

```bash
# Clone repository
git clone <repository-url>
cd Hack-Stair-AIML-1

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Start web server
./start_server.sh
```

Then open http://localhost:8000 in your browser.

### Option 3: MCP Server (for Claude Desktop)

Add to your Claude Desktop config (`~/.config/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "geopard": {
      "command": "python",
      "args": ["/path/to/Hack-Stair-AIML-1/mcp_server.py"]
    }
  }
}
```

## 📁 Project Structure

```
Hack-Stair-AIML-1/
├── README.md                    # This file
├── ARCHITECTURE.md              # System architecture & technical details
├── start_server.sh              # Web server startup script
├── mcp_server.py                # MCP server (CLI/Claude Desktop)
│
├── frontend/                    # Web interface
│   ├── chat_server_mcp.py       # FastAPI server with MCP integration
│   ├── index.html               # Chat UI
│   └── README.md                # Web server documentation
│
├── backend/                     # RAG system (Level 1-2)
│   ├── rag_setup.py             # Index creation
│   ├── rag_query.py             # Query engine
│   └── README.md                # RAG documentation
│
├── location-tools/              # Location services (Level 3)
│   ├── location_tools.py        # Core tools
│   ├── mcp_server.py            # Standalone MCP server
│   └── README.md                # Location tools documentation
│
└── data/
    └── products_ktlu.json       # Geodata metadata catalog
```

## 🔧 Components

### RAG System (`backend/`)
- **Technology**: Azure AI Search with L2 semantic ranking
- **Embeddings**: text-embedding-3-large (3072 dimensions)
- **Features**: Hybrid search, German language analysis, inline citations
- **Indexed**: ~500 datasets from Canton Luzern

### Location Tools (`location-tools/`)
- **API**: LocationFinder API integration
- **Features**: Address lookup, coordinate conversion, map URL generation
- **Supports**: Addresses, place names, EGID, EGRID, parcel numbers

### Web Interface (`frontend/`)
- **Framework**: FastAPI + vanilla JavaScript
- **Features**: Real-time chat, map integration, conversation history
- **Tools**: All 8 MCP tools available via function calling

## 💡 Example Queries

```
"Welche Höhendaten gibt es im Kanton Luzern?"
→ Returns DOM and DTM datasets with metadata and download links

"Zeige mir die Wildruhezonen in Emmen auf einer Karte"
→ Finds dataset + location + generates interactive map URL

"Ist die Adresse Mürgi 1, 6025 Neudorf von Verkehrslärm betroffen?"
→ Finds noise datasets + location + provides map with noise overlay
```

## 🛠️ Available Tools

The system provides 8 MCP tools:

### RAG & Dataset Search
- `search_datasets` - Find datasets by semantic search
- `ask_about_geodata` - Q&A with citations and sources

### Location & Mapping
- `search_location` - Geocoding via LocationFinder API
- `build_webmap_url` - Generate interactive map links
- `extract_location_from_query` - NLP location extraction
- `enrich_dataset_with_location` - Add spatial context

### Utilities
- `get_map_theme_for_dataset` - Suggest map visualization
- `build_geodatashop_links` - Download and metadata URLs

## 📚 Documentation

- **[DOCKER.md](DOCKER.md)** - Docker deployment guide (all platforms)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design
- **[frontend/README.md](frontend/README.md)** - Web server setup and usage
- **[backend/README.md](backend/README.md)** - RAG system details
- **[location-tools/README.md](location-tools/README.md)** - Location tools guide

## 🧪 Testing

```bash
# Test MCP server
python test_mcp_server.py

# Test RAG system
cd backend
python test_hackathon_questions.py

# Test location tools
cd location-tools
python test_mcp.py
```

## 🔐 Environment Variables

Required in `.env`:

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
EMBEDDING_MODEL=text-embedding-3-large
CHAT_MODEL=gpt-4o

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=geopard-rag-v2
```
