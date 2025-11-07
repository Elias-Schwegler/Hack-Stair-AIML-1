from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService

service = AzureSearchService()

# Test queries
test_queries = [
    "Höhendaten Terrain elevation",
    "Verkehrslärm Lärm noise",
    "Gewässer See water",
    "Gebäude building"
]

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)
    
    results = service.search(query, top=3)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   Type: {r['type']}")
        print(f"   Score: {r.get('score', 0):.3f}")
        print(f"   Keywords: {', '.join(r['keywords'][:5])}")
        print(f"   Metadata: {r['openly_url']}")