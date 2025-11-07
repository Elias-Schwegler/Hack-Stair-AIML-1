import json

# Load and inspect the JSON structure
with open('backend/data/products_ktlu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Type: {type(data)}")
print(f"Length: {len(data) if isinstance(data, list) else 'N/A'}")

if isinstance(data, list):
    print(f"\nFirst item keys: {data[0].keys() if data else 'Empty'}")
    print(f"\nFirst item sample:")
    print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
    
    # Count by data_type
    from collections import Counter
    types = Counter(item.get('data_type', 'unknown') for item in data)
    print(f"\nData types found:")
    for dtype, count in types.items():
        print(f"  {dtype}: {count}")
else:
    print(f"\nTop-level keys: {data.keys()}")