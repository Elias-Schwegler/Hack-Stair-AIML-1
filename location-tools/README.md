# Location Tools

> Spatial intelligence and location services for the Geopard system.

## Overview

Location-based tools that add spatial context to geodata queries through geocoding, interactive map generation, and dataset enrichment.

### Core Capabilities

- **LocationFinder API** - Convert addresses and place names to Swiss LV95 coordinates
- **Webmap URL Builder** - Generate interactive map URLs with zoom and markers
- **Geodatashop Links** - Direct links to data download and metadata
- **Smart Location Extraction** - NLP-based parsing of locations from natural language
- **Dataset Enrichment** - Add spatial context to search results

## Tools

### 1. LocationFinder API

Converts location queries to Swiss LV95 coordinates:

```python
from location_tools import LocationFinderTool

finder = LocationFinderTool()
results = finder.search("Bahnhof Luzern", limit=3)

for r in results:
    print(f"{r['name']}: ({r['cx']}, {r['cy']})")
```

**Supported location types:**
- Addresses (Strasse + Nummer + PLZ)
- Place names (Gemeinde, Ortsname, Flurname)
- EGID (Building ID)
- EGRID (Parcel ID)
- Gebäudeversicherungsnummer

### 2. Webmap URL Builder

Creates URLs for Luzern Webmaps with zoom and markers:

```python
from location_tools import WebmapURLBuilder

builder = WebmapURLBuilder()
url = builder.build_url(
    map_theme='hoehen',
    x=2666232,
    y=1211056,
    zoom=4515,
    add_marker=True
)
# Result: https://map.geo.lu.ch/hoehen?FOCUS=2666232:1211056:4515&marker
```

**Available map themes:**
- `grundbuchplan` - Cadastral maps
- `hoehen` - Height data
- `laerm` - Noise pollution
- `oberflaechengewaesser` - Surface water
- `amtliche_vermessung` - Official surveying

### 3. Geodatashop Links

Generate links to metadata and download pages:

```python
from location_tools import GeodatashopLinkBuilder

builder = GeodatashopLinkBuilder()
openly_link = builder.build_openly_link("DTM2024_DST")
shop_link = builder.build_shop_link("Digitales Terrainmodell")
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

## Integration with RAG

These tools can be integrated into RAG v2 for Level 3 functionality:

1. **Extract location from query** - Use LocationFinder to find coordinates
2. **Enrich dataset results** - Add webmap URLs with zoom to location
3. **Generate response** - Include map links in the answer

See `../backend` for the base RAG system.

## Dependencies

```bash
pip install requests
```

## Usage Example

```python
from location_tools import GeopardToolkit

toolkit = GeopardToolkit()

# Enrich a dataset result with location data
dataset = {
    'metauid': 'DTM2024_DST',
    'title': 'Digitales Terrainmodell 2024',
    'data_type': 'Datensatz'
}

enriched = toolkit.enrich_dataset_result(dataset, "Bahnhof Luzern")

print(f"Webmap URL: {enriched['webmap_url_with_location']}")
print(f"Coordinates: {enriched['location_coordinates']}")
print(f"Openly link: {enriched['openly_link']}")
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

## Roadmap

### Completed ✅
- [x] LocationFinder API integration
- [x] Webmap URL generation
- [x] Smart location extraction
- [x] Dataset enrichment
- [x] MCP server implementation

### Planned 📋
- [ ] Parse webmap feed.xml for complete catalog
- [ ] Dynamic zoom level calculation based on extent
- [ ] Location result caching
- [ ] Map preview/screenshot generation
