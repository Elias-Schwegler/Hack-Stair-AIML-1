import json

with open('backend/data/products_ktlu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Inspecting keywords field structure:\n")

for i, item in enumerate(data[:5]):  # Check first 5 items
    print(f"Item {i+1}: {item.get('title', 'No title')[:50]}")
    print(f"  Type: {item.get('data_type')}")
    keywords = item.get('keywords')
    print(f"  Keywords type: {type(keywords)}")
    print(f"  Keywords value: {keywords}")
    print()

# Find items with complex keyword structures
print("\nLooking for complex keyword structures...")
for item in data:
    keywords = item.get('keywords', [])
    if keywords and isinstance(keywords, list) and len(keywords) > 0:
        if not isinstance(keywords[0], str):
            print(f"Found non-string keywords in: {item.get('metauid')}")
            print(f"  Type: {type(keywords[0])}")
            print(f"  Value: {keywords[0]}")
            break