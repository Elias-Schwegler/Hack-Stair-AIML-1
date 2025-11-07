import json
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService

# Load data
with open('backend/data/products_ktlu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

service = AzureSearchService()

# Get first collection
collection = [item for item in data if item.get('data_type') == 'Kollektion'][0]

print(f"Testing with: {collection.get('title')}")
print(f"metauid: {collection.get('metauid')}\n")

# Build document
doc = service._build_document(collection, 'collection')

print("Document structure:")
for key, value in doc.items():
    if isinstance(value, list):
        print(f"  {key}: List[{type(value[0]).__name__ if value else 'empty'}] (len={len(value)})")
    else:
        print(f"  {key}: {type(value).__name__}")

print("\nTesting JSON serialization...")
try:
    json_str = json.dumps(doc, ensure_ascii=False)
    print(f"✅ JSON OK ({len(json_str)} chars)")
except Exception as e:
    print(f"❌ JSON failed: {e}")
    exit(1)

print("\nTesting Azure upload...")
try:
    result = service.search_client.upload_documents(documents=[doc])
    if result[0].succeeded:
        print(f"✅ Upload successful!")
        print(f"   Document key: {result[0].key}")
    else:
        print(f"❌ Upload failed!")
        print(f"   Error: {result[0].error_message}")
except Exception as e:
    print(f"❌ Upload exception: {e}")
    import traceback
    traceback.print_exc()