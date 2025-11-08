from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService
import json

service = AzureSearchService()

# Search for DTM datasets
print("Searching for DTM/Höhendaten services...")
print("="*60)

results = service.search("DTM Terrainmodell Höhe elevation", top=10)

for r in results:
    if r.get('services') and len(r['services']) > 0:
        print(f"\n✅ {r['title']}")
        print(f"   Type: {r['type']}")
        print(f"   Services: {r['services']}")
        print(f"   Metadata: {r['openly_url']}")

# Also check the raw JSON for service URLs
print("\n" + "="*60)
print("Checking raw JSON for service information...")
print("="*60)

with open('backend/data/products_ktlu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find DTM related items with services
for item in data:
    title = item.get('title', '').lower()
    if 'dtm' in title or 'terrain' in title or 'höhenmodell' in title:
        print(f"\n📊 {item.get('title')}")
        print(f"   metauid: {item.get('metauid')}")
        print(f"   data_type: {item.get('data_type')}")
        
        # Check for services
        services = item.get('services', [])
        if services:
            print(f"   Services ({len(services)}):")
            for svc in services[:3]:  # Show first 3
                if isinstance(svc, dict):
                    print(f"      - {svc.get('title', 'N/A')}")
                    print(f"        metauid: {svc.get('metauid')}")
                    
                    # Check for resources/endpoints
                    elements = svc.get('elements', [])
                    if elements:
                        for elem in elements:
                            resources = elem.get('resources', [])
                            for res in resources:
                                if 'MapServer' in res.get('format', '') or 'WMS' in res.get('format', ''):
                                    print(f"        URL: {res.get('path')}")