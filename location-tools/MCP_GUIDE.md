# MCP Server for Geopard Location Tools

This MCP (Model Context Protocol) server exposes the Geopard location tools as callable functions for AI assistants.

## Features

The server provides 7 tools:

### 1. `search_location`
Search for locations in Canton Luzern using the LocationFinder API.

**Parameters:**
- `query` (string, required): Location search query
- `limit` (integer, optional): Max results (default: 10)
- `filter_type` (string, optional): Filter by type (Adresse, Gemeinde, EGID, etc.)

**Example:**
```json
{
  "query": "Bahnhof Luzern",
  "limit": 3
}
```

### 2. `get_coordinates`
Get center coordinates for a location (simplified search).

**Parameters:**
- `query` (string, required): Location query

**Returns:** `{x, y}` coordinates or null

### 3. `build_webmap_url`
Build interactive map URLs with zoom and markers.

**Parameters:**
- `map_theme` (string, optional): Map type (grundbuchplan, hoehen, laerm, etc.)
- `x` (number, optional): X coordinate
- `y` (number, optional): Y coordinate
- `zoom` (integer, optional): Zoom level (default: 4515)
- `add_marker` (boolean, optional): Add marker (default: true)

**Example:**
```json
{
  "map_theme": "hoehen",
  "x": 2666232,
  "y": 1211056,
  "zoom": 4515,
  "add_marker": true
}
```

### 4. `get_map_theme_for_dataset`
Suggest the best map theme for a dataset.

**Parameters:**
- `dataset_title` (string, required): Dataset title to analyze

### 5. `build_geodatashop_links`
Generate download and metadata links.

**Parameters:**
- `metauid` (string, optional): Dataset metadata UID
- `search_term` (string, optional): Search term

### 6. `enrich_dataset_with_location`
Complete enrichment: adds location data, webmap URLs, and shop links.

**Parameters:**
- `dataset` (object, required): Dataset metadata
- `user_query` (string, optional): User's query (for location extraction)

### 7. `extract_location_from_query`
Extract location information from natural language queries.

**Parameters:**
- `query` (string, required): User query

## Installation

1. Install dependencies:
```bash
pip install mcp requests
```

2. Make the server executable:
```bash
chmod +x mcp_server.py
```

## Running the Server

### Standalone Test
```bash
python mcp_server.py
```

### Integration with MCP-compatible tools

Add to your MCP configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "geopard-location-tools": {
      "command": "python",
      "args": [
        "/path/to/location-tools/mcp_server.py"
      ]
    }
  }
}
```

Or use the provided config:
```bash
# Copy to Claude Desktop config location
cp mcp_config.json ~/.config/Claude/claude_desktop_config.json
```

## Testing

Test individual tools:

```bash
# Example: Search location
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_location", "arguments": {"query": "Bahnhof Luzern", "limit": 1}}, "id": 1}' | python mcp_server.py
```

## Usage Examples

### Example 1: Find location and build map URL
```python
# Step 1: Search location
search_location(query="Bahnhof Luzern", limit=1)
# Returns: coordinates (2666232, 1211056)

# Step 2: Build map URL
build_webmap_url(
    map_theme="hoehen",
    x=2666232,
    y=1211056,
    zoom=4515,
    add_marker=True
)
# Returns: https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker
```

### Example 2: Enrich dataset for Level 3 response
```python
dataset = {
    "metauid": "DTM2024_DS",
    "title": "Digitales Terrainmodell 2024",
    "data_type": "Datensatz"
}

enrich_dataset_with_location(
    dataset=dataset,
    user_query="Bahnhof Luzern"
)

# Returns enriched dataset with:
# - webmap_url_with_location
# - location_coordinates
# - openly_link
# - shop_search_link
```

### Example 3: Extract location from natural query
```python
extract_location_from_query(
    query="Auf welcher Höhe liegt der Torbogen des Bahnhofs Luzern?"
)

# Returns location info if found
```

## Integration with RAG

The MCP server can be integrated with the RAG system for Level 3 responses:

1. User asks about specific location
2. RAG retrieves relevant datasets
3. MCP extracts location from query
4. MCP enriches datasets with webmap URLs
5. Response includes interactive map links

## Error Handling

All tools return JSON with `success` field:

```json
{
  "success": true,
  "data": {...}
}
```

Or on error:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Dependencies

- `mcp` - Model Context Protocol SDK
- `requests` - HTTP library for LocationFinder API
- Python 3.10+

## Architecture

```
┌─────────────────────┐
│   AI Assistant      │
│   (Claude, GPT)     │
└──────────┬──────────┘
           │ MCP Protocol
           │
┌──────────▼──────────┐
│  mcp_server.py      │
│  (MCP Interface)    │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  location_tools.py  │
│  (Core Logic)       │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  LocationFinder API │
│  Webmap URLs        │
└─────────────────────┘
```

## Next Steps

- [ ] Add caching for LocationFinder results
- [ ] Add map preview/screenshot generation
- [ ] Integrate with webmap feed.xml parser
- [ ] Add spatial query tools (WFS/ESRI)
- [ ] Support batch location enrichment
