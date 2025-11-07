import json
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService

def validate_document(doc, doc_id):
    """Check if document has any nested structures"""
    issues = []
    
    for key, value in doc.items():
        if isinstance(value, list):
            if len(value) == 0:
                continue
            
            # Check first element
            first = value[0]
            if isinstance(first, list):
                issues.append(f"  ❌ {key}: Contains nested list")
                issues.append(f"     First element: {first}")
            elif isinstance(first, dict):
                issues.append(f"  ❌ {key}: Contains dict in list")
                issues.append(f"     First element: {first}")
            elif not isinstance(first, (str, int, float, bool)):
                issues.append(f"  ❌ {key}: Contains {type(first).__name__}")
                issues.append(f"     First element: {first}")
    
    return issues

# Load data
print("Loading metadata...")
with open('backend/data/products_ktlu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

service = AzureSearchService()

print("Processing first 50 documents...\n")

collections = [item for item in data if item.get('data_type') == 'Kollektion'][:50]
datasets = [item for item in data if item.get('data_type') == 'Datensatz'][:50]

all_items = collections + datasets

bad_docs = []

for idx, item in enumerate(all_items, 1):
    try:
        item_type = 'collection' if item.get('data_type') == 'Kollektion' else 'dataset'
        doc = service._build_document(item, item_type)
        
        issues = validate_document(doc, item.get('metauid'))
        
        if issues:
            print(f"\n❌ Document {idx}: {item.get('title')}")
            print(f"   metauid: {item.get('metauid')}")
            for issue in issues:
                print(issue)
            bad_docs.append((item.get('metauid'), issues))
            
            # Print the raw data for this field
            print(f"\n   Raw item data:")
            for key in ['keywords', 'services']:
                print(f"   {key}: {item.get(key)}")
        
        # Try JSON serialization
        try:
            json.dumps(doc)
        except Exception as e:
            print(f"\n❌ JSON Serialization failed for {item.get('metauid')}")
            print(f"   Error: {e}")
            bad_docs.append((item.get('metauid'), [str(e)]))
    
    except Exception as e:
        print(f"\n❌ Building document failed for {item.get('metauid')}")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

if bad_docs:
    print(f"\n{'='*60}")
    print(f"Found {len(bad_docs)} problematic documents")
    print('='*60)
    for metauid, issues in bad_docs:
        print(f"  - {metauid}")
else:
    print(f"\n✅ All {len(all_items)} documents validated successfully!")