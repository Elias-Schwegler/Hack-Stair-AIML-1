import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService

service = AzureSearchService()

print("Deleting old index...")
try:
    service.index_client.delete_index(service.index_name)
    print(f"✅ Deleted index: {service.index_name}")
except Exception as e:
    print(f"⚠️ Could not delete (might not exist): {e}")

import time
print("\nWaiting 5 seconds...")
time.sleep(5)

print("\nCreating new index...")
service.create_index()

print("\n✅ Index recreated successfully!")
print("\nYou can now run: python backend/services/azure_search_service.py")