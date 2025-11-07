import json
import os
from typing import List, Dict
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)
from openai import AzureOpenAI

class AzureSearchService:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.api_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
        
        # Azure OpenAI for embeddings
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.credential = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential
        )
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
    
    def create_index(self):
        """Create the search index with vector search capabilities"""
        
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="metauid", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="type", type=SearchFieldDataType.String, filterable=True),
            
            SearchableField(
                name="title",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="de.microsoft"
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="de.microsoft"
            ),
            SearchableField(
                name="keywords",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True
            ),
            
            # URLs and metadata
            SimpleField(name="openly_url", type=SearchFieldDataType.String),
            SimpleField(name="webapp_url", type=SearchFieldDataType.String),
            SimpleField(name="data_type", type=SearchFieldDataType.String, filterable=True),
            
            # Services
            SimpleField(
                name="services",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String)
            ),
            
            # Vector field for embeddings
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile"
            )
        ]
        
        # Vector search configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="hnsw-config")
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config"
                )
            ]
        )
        
        # Semantic search configuration
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="title"),
                        content_fields=[
                            SemanticField(field_name="content")
                        ],
                        keywords_fields=[
                            SemanticField(field_name="keywords")
                        ]
                    )
                )
            ]
        )
        
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        # Create or update index
        self.index_client.create_or_update_index(index)
        print(f"✅ Index '{self.index_name}' created/updated successfully")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI"""
        # Truncate text if too long (max 8191 tokens for ada-002)
        if len(text) > 8000:
            text = text[:8000]
        
        response = self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    
    def _build_document(self, item: Dict, item_type: str) -> Dict:
        """Build a search document from metadata item"""
        
        title = item.get('title', '') or ''
        purpose = item.get('abstract', '') or item.get('purpose', '') or ''
        keywords_raw = item.get('keywords', [])
        
        # Flatten keywords to list
        keywords = []
        if keywords_raw and isinstance(keywords_raw, list):
            for kw in keywords_raw:
                if isinstance(kw, str):
                    keywords.append(kw)
                elif isinstance(kw, dict):
                    name = kw.get('name') or kw.get('keyword') or kw.get('label')
                    if name:
                        keywords.append(str(name))
        
        # Convert to comma-separated string for schema
        keywords_string = ', '.join(keywords) if keywords else ''
        
        keyword_text = ' '.join(keywords)
        content = f"{title}. {purpose} {keyword_text}".strip()
        
        if not content or content == '.':
            content = title or 'Kein Inhalt verfügbar'
        
        # Generate embedding
        try:
            embedding = self._get_embedding(content)
        except Exception as e:
            print(f"    ⚠️ Embedding skipped for {item.get('metauid')}: {e}")
            embedding = [0.0] * 1536
        
        # Get URLs
        urls = item.get('urls', {}) or {}
        openly_url = None
        webapp_url = None
        
        if isinstance(urls, dict):
            openly = urls.get('openly', {})
            webapp = urls.get('webapp', {})
            openly_url = openly.get('url') if isinstance(openly, dict) else None
            webapp_url = webapp.get('url') if isinstance(webapp, dict) else None
        
        # Flatten services to list of strings
        services_raw = item.get('services', []) or []
        services = []
        if isinstance(services_raw, list):
            for svc in services_raw:
                if isinstance(svc, dict):
                    metauid = svc.get('metauid')
                    if metauid:
                        services.append(str(metauid))
                elif isinstance(svc, str):
                    services.append(svc)
        
        # Build document matching the schema
        doc = {
            'id': str(item['metauid']),
            'metauid': str(item['metauid']),
            'type': str(item_type),
            'title': str(title or 'Ohne Titel'),
            'content': str(content),
            'keywords': keywords_string,  # ⭐ STRING not array!
            'openly_url': str(openly_url) if openly_url else None,
            'webapp_url': str(webapp_url) if webapp_url else None,
            'content_vector': embedding,  # Array is OK for this field
            'data_type': str(item.get('data_type')) if item.get('data_type') else None,
            'services': services  # Array is OK for this field
        }
        
        return doc
    
    def index_metadata(self, json_path: str):
        """Index all metadata from products_ktlu.json"""
        
        print("Loading metadata...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("❌ Expected a list, got:", type(data))
            return
        
        print(f"Found {len(data)} items total")
        
        # Separate by type
        collections = [item for item in data if item.get('data_type') == 'Kollektion']
        datasets = [item for item in data if item.get('data_type') == 'Datensatz']
        references = [item for item in data if item.get('data_type') == 'Referenz']
        
        print(f"  - {len(collections)} Kollektionen")
        print(f"  - {len(datasets)} Datensätze")
        print(f"  - {len(references)} Referenzen")
        
        documents = []
        
        # Process collections
        print("\nProcessing Kollektionen...")
        for idx, collection in enumerate(collections, 1):
            try:
                doc = self._build_document(collection, 'collection')
                documents.append(doc)
                if idx % 10 == 0:
                    print(f"  {idx}/{len(collections)} processed...")
            except Exception as e:
                print(f"  ⚠️ Error processing {collection.get('metauid', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Process datasets
        print("\nProcessing Datensätze...")
        for idx, dataset in enumerate(datasets, 1):
            try:
                doc = self._build_document(dataset, 'dataset')
                documents.append(doc)
                if idx % 20 == 0:
                    print(f"  {idx}/{len(datasets)} processed...")
            except Exception as e:
                print(f"  ⚠️ Error processing {dataset.get('metauid', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Process references (services)
        print("\nProcessing Referenzen...")
        for idx, reference in enumerate(references, 1):
            try:
                doc = self._build_document(reference, 'service')
                documents.append(doc)
                if idx % 10 == 0:
                    print(f"  {idx}/{len(references)} processed...")
            except Exception as e:
                print(f"  ⚠️ Error processing {reference.get('metauid', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n✅ Successfully prepared {len(documents)} documents")
        print(f"   ({len([d for d in documents if d['type']=='collection'])} collections, "
              f"{len([d for d in documents if d['type']=='dataset'])} datasets, "
              f"{len([d for d in documents if d['type']=='service'])} services)")
        
        print(f"\nUploading to Azure AI Search...")
        
        # Upload in batches
        batch_size = 50
        total_batches = (len(documents) - 1) // batch_size + 1
        successful_uploads = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            try:
                result = self.search_client.upload_documents(documents=batch)
                succeeded = sum(1 for r in result if r.succeeded)
                successful_uploads += succeeded
                
                if succeeded == len(batch):
                    print(f"  ✅ Batch {batch_num}/{total_batches}: {succeeded}/{len(batch)} documents")
                else:
                    print(f"  ⚠️ Batch {batch_num}/{total_batches}: {succeeded}/{len(batch)} documents (some failed)")
                    for r in result:
                        if not r.succeeded:
                            print(f"     Failed: {r.key} - {r.error_message}")
                            
            except Exception as e:
                print(f"  ❌ Batch {batch_num}/{total_batches} failed: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🎉 Indexing complete! {successful_uploads}/{len(documents)} documents uploaded successfully")
    
    def search(
        self,
        query: str,
        top: int = 5,
        use_vector: bool = True,
        use_semantic: bool = True
    ) -> List[Dict]:
        """Search the index using hybrid search"""
        
        from azure.search.documents.models import VectorizedQuery
        
        # Build vector query with proper format
        vector_queries = None
        if use_vector:
            try:
                query_vector = self._get_embedding(query)
                vector_queries = [
                    VectorizedQuery(
                        vector=query_vector,
                        k_nearest_neighbors=top,
                        fields="content_vector"
                    )
                ]
            except Exception as e:
                print(f"⚠️ Vector search disabled: {e}")
                vector_queries = None
        
        # Perform search
        results = self.search_client.search(
            search_text=query,
            vector_queries=vector_queries,
            query_type="semantic" if use_semantic else "simple",
            semantic_configuration_name="semantic-config" if use_semantic else None,
            top=top
        )
        
        formatted_results = []
        for result in results:
            # Parse keywords string back to list
            keywords_str = result.get('keywords', '')
            keywords = [k.strip() for k in keywords_str.split(',') if k.strip()] if keywords_str else []
            
            formatted_results.append({
                'id': result['id'],
                'metauid': result['metauid'],
                'type': result['type'],
                'title': result['title'],
                'content': result['content'],
                'keywords': keywords,
                'openly_url': result.get('openly_url'),
                'webapp_url': result.get('webapp_url'),
                'data_type': result.get('data_type'),
                'services': result.get('services', []),
                'score': result.get('@search.score'),
                'reranker_score': result.get('@search.reranker_score')
            })
        
        return formatted_results


# Run indexing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    service = AzureSearchService()
    
    # Create index
    print("Creating index...")
    service.create_index()
    
    # Index metadata
    print("\nIndexing metadata...")
    service.index_metadata("backend/data/products_ktlu.json")
    
    # Test search
    print("\n" + "="*60)
    print("Testing search...")
    print("="*60)
    results = service.search("Höhendaten Terrain elevation")
    for r in results:
        print(f"✓ {r['title']}")
        print(f"  Type: {r['type']}, Score: {r['score']:.3f}")
        print(f"  URL: {r['openly_url']}")
        print()