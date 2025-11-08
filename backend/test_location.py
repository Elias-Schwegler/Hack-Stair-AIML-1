import asyncio
import httpx
import json

async def test_location_finder():
    """Test the LocationFinder API directly"""
    
    base_url = "https://svc.geo.lu.ch/locationfinder/api/v1/lookup"
    
    query = "Bahnhof Luzern"
    
    print(f"Testing: '{query}'")
    print('='*60)
    
    params = {
        "query": query,
        "limit": 5
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url, params=params)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Print the raw structure
                print("\nRaw response structure:")
                print(f"Type: {type(data)}")
                print(f"\nFull response:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_location_finder())