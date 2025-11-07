import json
import os
from dotenv import load_dotenv
load_dotenv()

# Import the service
import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService

# Load data
with open('backend/data/products_ktlu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get first item from each type
collection = [item for item in data if item.get('data_type') == 'Kollektion'][0]
dataset = [item for item in data if item.get('data_type') == 'Datensatz'][0]
reference = [item for item in data if item.get('data_type') == 'Referenz'][0]

service = AzureSearchService()

print("Building sample documents...\n")

for name, item, item_type in [
    ("Collection", collection, "collection"),
    ("Dataset", dataset, "dataset"),
    ("Reference", reference, "service")
]:
    print(f"\n{'='*60}")
    print(f"{name}: {item.get('title')}")
    print('='*60)
    
    try:
        # Build without embedding first
        doc = service._build_document(item, item_type)
        
        # Check each field type
        for key, value in doc.items():
            value_type = type(value).__name__
            
            # Check for nested arrays
            if isinstance(value, list) and len(value) > 0:
                first_elem_type = type(value[0]).__name__
                if isinstance(value[0], list):
                    print(f"  ❌ {key}: List[List] - PROBLEM!")
                    print(f"     Value: {value[:2]}")
                else:
                    print(f"  ✓ {key}: List[{first_elem_type}] ({len(value)} items)")
            elif value is None:
                print(f"  ✓ {key}: None")
            else:
                print(f"  ✓ {key}: {value_type}")
        
        # Try to serialize to JSON (what Azure does)
        json_str = json.dumps(doc, ensure_ascii=False)
        print(f"\n  ✅ JSON serialization successful ({len(json_str)} chars)")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()