import os
from dotenv import load_dotenv
load_dotenv()

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

credential = AzureKeyCredential(api_key)
index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

print(f"Fetching schema for index: {index_name}\n")

try:
    index = index_client.get_index(index_name)
    
    print("Index Fields:")
    print("=" * 60)
    for field in index.fields:
        field_type = str(field.type)
        print(f"{field.name:20} | {field_type:30} | Key: {field.key}")
    
except Exception as e:
    print(f"Error: {e}")