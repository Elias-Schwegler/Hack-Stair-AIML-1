# Location Tools

> Spatial intelligence for Geopard: geocoding, elevation, maps, and coordinate transformation.

## Features

- **LocationFinder API** - Swiss LV95 coordinates from addresses/places
- **Height Queries** - Swiss elevation data (swissALTI3D, 0.5-2m resolution)
- **Coordinate Transform** - WGS84 ↔ LV95 conversion (<1m accuracy)
- **Webmap URLs** - Interactive maps with zoom and markers
- **Geodatashop Links** - Direct download and metadata access

## Quick Start

## Quick Start

### Location Search

```python
from location_tools import LocationFinderTool

finder = LocationFinderTool()
results = finder.search("Bahnhof Luzern", limit=3)
for r in results:
    print(f"{r['name']}: ({r['cx']}, {r['cy']})")
```

### Height Queries ⛰️

```python
from height_tools import HeightQueryToolkit

toolkit = HeightQueryToolkit()

# By location name
result = toolkit.query_height_by_location_name("Bahnhof Luzern")
print(f"Height: {result['height_text']}")  # "436.1 m ü. M."

# By coordinates
result = toolkit.query_height_wgs84(47.0501682, 8.3093072)
result = toolkit.query_height_lv95(2666232, 1211056)
```

### Webmap URLs

```python
from location_tools import WebmapURLBuilder

builder = WebmapURLBuilder()
url = builder.build_url('hoehen', x=2666232, y=1211056, zoom=4515, add_marker=True)
# https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker
```

**Map themes**: `hoehen`, `grundbuchplan`, `laerm`, `oberflaechengewaesser`, `amtliche_vermessung`

## Testing

```bash
python location_tools.py      # Test location finder
python test_height.py         # Test height queries
python test_mcp_height.py     # Test MCP server
```

## Testing

Run the test script:

```bash
python location_tools.py
```

Expected output:
```
Testing LocationFinder:
  - Bahnhof, 6003 Luzern (Flurname): 2666232, 1211056
  - Bahnhof, 6005 Luzern (Flurname): 2666355, 1211022
  - Bahnhof, 6014 Luzern (Flurname): 2662143, 1211756

Testing Webmap URL:
  URL: https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker

Testing dataset enrichment:
  Openly: https://www.geo.lu.ch/openly/dataset/DTM2024_DST
  Webmap: https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker
```

## MCP Servers

### Location Tools (`mcp_server.py`)
`search_location`, `get_coordinates`, `build_webmap_url`, `enrich_dataset_with_location`

### Height Tools (`mcp_server_height.py`)
`get_height_by_name`, `get_height_at_location`, `get_elevation_profile`, `convert_wgs84_to_lv95`, `convert_lv95_to_wgs84`, `get_height_with_webmap`

**Config**: Add to `mcp_config.json`
```json
{
  "mcpServers": {
    "geopard-height-tools": {
      "command": "python",
      "args": ["location-tools/mcp_server_height.py"]
    }
  }
}
```

## Integration

### With MCP Server

See [MCP_GUIDE.md](MCP_GUIDE.md) for complete MCP server documentation.

### With RAG System

```python
from location_tools import GeopardToolkit
from rag_query import StateOfTheArtGeopardRAG

toolkit = GeopardToolkit()
rag = StateOfTheArtGeopardRAG()

# Search datasets
results = rag.query("Höhendaten")

# Enrich with location
enriched = toolkit.enrich_dataset_result(
    results['sources'][0],
    "Bahnhof Luzern"
)
```

## Data Sources

- **LocationFinder**: `svc.geo.lu.ch/locationfinder` (Canton Luzern geocoding)
- **Height API**: `api3.geo.admin.ch/rest/services/height` (swissALTI3D, 0.5-2m resolution, LHN95)
- **Profile API**: `api3.geo.admin.ch/rest/services/profile.json` (elevation profiles)

---

**Dependencies**: `requests`  
**Part of**: Geopard RAG for HackSTAIR 2025
