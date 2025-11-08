"""
State-of-the-Art RAG Setup for Geopard Metadata (2025)

Features:
- text-embedding-3-large (3072-dim) for superior semantic understanding
- Azure AI Search semantic ranking (L2 reranker)
- Advanced chunking with overlap for better context
- Semantic configuration for hybrid search
- Optimized for production Azure environments
"""

import json
import os
import time
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticField, SemanticPrioritizedFields,
    SemanticSearch
)
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()


class StateOfTheArtGeopardRAG:
    """
    State-of-the-art RAG setup for Geopard metadata catalog (2025)
    - text-embedding-3-large (3072-dim) embeddings
    - Azure AI Search semantic ranking
    - Advanced chunking with overlap
    - Optimized HNSW parameters
    - Semantic search configuration
    """
    
    def __init__(self):
        # Azure OpenAI setup
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not azure_endpoint or not azure_key:
            raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")
        
        self.openai_client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            api_key=azure_key
        )
        
        # Azure Search setup
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        
        if not search_endpoint or not search_key:
            raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set")
        
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=AzureKeyCredential(search_key)
        )
        
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "geopard-rag-v2")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.embedding_dimensions = 3072  # text-embedding-3-large dimensions
        
    def load_geopard_data(self, file_path: str) -> List[Dict]:
        """Load Geopard metadata from JSON file"""
        print(f"Loading Geopard metadata from {file_path}...")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"File size: {file_size_mb:.1f} MB")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Data is a list of items (Collections, Datasets, Services)
        items = data if isinstance(data, list) else [data]
        print(f"Loaded {len(items)} items")
        return items
    
    def create_chunks(self, item: Dict) -> List[Tuple[str, Dict]]:
        """
        Create overlapping chunks from Geopard item with semantic boundaries
        
        Returns:
            List of (chunk_text, metadata) tuples
        """
        # For now, create main chunk + abstract chunk for better retrieval
        chunks = []
        
        # Main chunk with full context
        main_text, metadata = self._extract_searchable_content(item)
        chunks.append((main_text, metadata))
        
        # If abstract is long, create dedicated abstract chunk
        abstract = item.get('abstract', '')
        if abstract and len(abstract) > 200:
            abstract_text = f"Title: {item.get('title', '')}\n\nDetailed Description:\n{abstract}"
            if item.get('keywords'):
                abstract_text += f"\n\nKeywords: {', '.join(item['keywords'])}"
            
            abstract_metadata = metadata.copy()
            abstract_metadata['chunk_type'] = 'abstract'
            chunks.append((abstract_text, abstract_metadata))
        
        return chunks
    
    def _extract_searchable_content(self, item: Dict) -> Tuple[str, Dict]:
        """
        Extract searchable text and metadata from a Geopard item
        
        Returns:
            (searchable_text, metadata_dict)
        """
        data_type = item.get('data_type', 'Unknown')
        metauid = item.get('metauid', '')
        title = item.get('title', '')
        
        # Build searchable text content
        text_parts = []
        
        # Title is most important
        if title:
            text_parts.append(f"Title: {title}")
        
        # Purpose and abstract are critical for understanding
        if item.get('purpose'):
            text_parts.append(f"Purpose: {item['purpose']}")
        
        if item.get('abstract'):
            text_parts.append(f"Abstract: {item['abstract']}")
        
        # Keywords are essential for search
        keywords = item.get('keywords', [])
        if keywords:
            keywords_str = ', '.join(keywords)
            text_parts.append(f"Keywords: {keywords_str}")
        
        # Feature type for datasets
        if item.get('feature_type'):
            text_parts.append(f"Feature Type: {item['feature_type']}")
        
        # Service type for services
        if item.get('service_type'):
            text_parts.append(f"Service Type: {item['service_type']}")
        
        # Constraints
        constraints = item.get('resourceconstraint_names', [])
        if constraints:
            text_parts.append(f"Access: {', '.join(constraints)}")
        
        # Contact information
        contact_spec = item.get('contact_spec', {})
        if contact_spec and isinstance(contact_spec, dict):
            org = contact_spec.get('organisation', '')
            if org:
                text_parts.append(f"Contact: {org}")
        
        # Extract WMS/WFS URLs from services
        services = item.get('services', [])
        wms_urls = []
        wfs_urls = []
        for service in services:
            if isinstance(service, dict):
                elements = service.get('elements', [])
                for element in elements:
                    if isinstance(element, dict):
                        resources = element.get('resources', [])
                        for resource in resources:
                            if isinstance(resource, dict):
                                path = resource.get('path', '')
                                if 'WMSServer' in path and path not in wms_urls:
                                    wms_urls.append(path)
                                elif 'WFSServer' in path and path not in wfs_urls:
                                    wfs_urls.append(path)
        
        # Add URLs to searchable text
        if wms_urls:
            text_parts.append(f"WMS Service: {wms_urls[0]}")
        if wfs_urls:
            text_parts.append(f"WFS Service: {wfs_urls[0]}")
        
        searchable_text = "\n".join(text_parts)
        
        # Extract structured metadata
        metadata = {
            'metauid': metauid,
            'title': title,
            'data_type': data_type,
            'keywords': keywords,
            'purpose': item.get('purpose', ''),
            'abstract': item.get('abstract', ''),
            'feature_type': item.get('feature_type', ''),
            'service_type': item.get('service_type', ''),
            'parent_metauid': item.get('parent_metauid', ''),
            'constraints': constraints,
            'urls': item.get('urls', {}),
            'datestamp': item.get('datestamp', ''),
            'chunk_type': 'main',
        }
        
        return searchable_text, metadata
    
    def generate_embedding(self, text: str, retry_count: int = 0) -> Optional[List[float]]:
        """Generate embedding for text with rate limit handling"""
        try:
            # Truncate if too long (8191 is max for text-embedding-3-large)
            text = text[:8000]
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            
            # Validate embedding dimensions
            if len(embedding) != self.embedding_dimensions:
                print(f"  ⚠️  Warning: Expected {self.embedding_dimensions} dims, got {len(embedding)}")
            
            return embedding
        except Exception as e:
            error_str = str(e)
            if '429' in error_str and retry_count < 5:
                # Rate limit hit, wait and retry
                wait_time = (retry_count + 1) * 10  # Progressive backoff
                print(f"  ⏳ Rate limit, waiting {wait_time}s (attempt {retry_count + 1}/5)...")
                time.sleep(wait_time)
                return self.generate_embedding(text, retry_count + 1)
            elif 'quota' in error_str.lower():
                print(f"  ❌ Quota exceeded: {e}")
                return None
            elif 'authentication' in error_str.lower() or 'unauthorized' in error_str.lower():
                print(f"  ❌ Authentication error: {e}")
                return None
            else:
                print(f"  ❌ Error generating embedding: {e}")
                return None
    
    def create_search_index(self):
        """
        Create Azure AI Search index with semantic search and rich metadata
        """
        print(f"Creating search index: {self.index_name}")
        
        # Define index fields with structure-aware metadata
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="de.lucene"),
            SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="de.lucene"),
            SimpleField(name="metauid", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="data_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="keywords", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
            SearchableField(name="purpose", type=SearchFieldDataType.String, analyzer_name="de.lucene"),
            SearchableField(name="abstract", type=SearchFieldDataType.String, analyzer_name="de.lucene"),
            SimpleField(name="feature_type", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="service_type", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="parent_metauid", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="constraints", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
            SimpleField(name="openly_url", type=SearchFieldDataType.String),
            SimpleField(name="webapp_url", type=SearchFieldDataType.String),
            SimpleField(name="datestamp", type=SearchFieldDataType.String, sortable=True),
            SimpleField(name="chunk_type", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.embedding_dimensions,
                vector_search_profile_name="geopard-vector-profile"
            ),
        ]
        
        # Configure vector search with optimized HNSW parameters for 3072-dim
        from azure.search.documents.indexes.models import HnswParameters
        
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="geopard-hnsw",
                    parameters=HnswParameters(
                        m=8,  # Increased for higher-dim embeddings
                        ef_construction=400,  # Optimized for quality/speed balance
                        ef_search=500,  # Optimized for recall/speed balance
                        metric="cosine"
                    )
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="geopard-vector-profile",
                    algorithm_configuration_name="geopard-hnsw"
                )
            ]
        )
        
        # Configure semantic search (L2 reranker)
        semantic_config = SemanticConfiguration(
            name="geopard-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[
                    SemanticField(field_name="content"),
                    SemanticField(field_name="abstract"),
                    SemanticField(field_name="purpose")
                ],
                keywords_fields=[
                    SemanticField(field_name="keywords")
                ]
            )
        )
        
        semantic_search = SemanticSearch(
            configurations=[semantic_config]
        )
        
        # Create index with semantic search
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        try:
            result = self.index_client.create_or_update_index(index)
            print(f"✅ Index '{result.name}' created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating index: {e}")
            return False
    
    def process_and_index_items(self, file_path: str, batch_size: int = 50):
        """
        Process Geopard items and upload to search index
        Each Collection, Dataset, and Service becomes a separate searchable document
        """
        items = self.load_geopard_data(file_path)
        
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        
        if not search_endpoint or not search_key:
            raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set")
        
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(search_key)
        )
        
        documents_to_upload = []
        stats = {'collections': 0, 'datasets': 0, 'services': 0, 'other': 0, 'failed': 0, 'chunks': 0}
        
        print("\n📊 Processing Geopard items...")
        print(f"Total items to process: {len(items)}")
        print(f"Batch size: {batch_size} documents\n")
        
        for idx, item in enumerate(items):
            try:
                # Progress indicator (every item)
                if (idx + 1) % 10 == 0:
                    print(f"Progress: {idx + 1}/{len(items)} items ({(idx+1)/len(items)*100:.1f}%)")
                
                # Create chunks with overlap
                chunks = self.create_chunks(item)
                
                # Track statistics ONCE per item (before chunk loop)
                data_type = item.get('data_type', '').lower()
                if 'kollektion' in data_type or 'collection' in data_type:
                    stats['collections'] += 1
                elif 'datensatz' in data_type or 'dataset' in data_type:
                    stats['datasets'] += 1
                elif 'dienst' in data_type or 'service' in data_type:
                    stats['services'] += 1
                else:
                    stats['other'] += 1
                
                # Process each chunk
                for chunk_idx, (searchable_text, metadata) in enumerate(chunks):
                    # Generate embedding
                    embedding = self.generate_embedding(searchable_text)
                    
                    if not embedding:
                        stats['failed'] += 1
                        continue
                    
                    stats['chunks'] += 1
                    
                    # Prepare document for indexing
                    doc_id = metadata['metauid'] if metadata['metauid'] else f"item_{idx}"
                    if chunk_idx > 0:
                        doc_id = f"{doc_id}_chunk{chunk_idx}"
                    
                    # Extract URLs - ensure they are strings, not objects
                    urls = metadata.get('urls', {})
                    if isinstance(urls, dict):
                        openly_url = urls.get('openly', '')
                        webapp_url = urls.get('webapp', '')
                        # Convert to string if it's a dict/object
                        if isinstance(openly_url, dict):
                            openly_url = json.dumps(openly_url) if openly_url else ''
                        if isinstance(webapp_url, dict):
                            webapp_url = json.dumps(webapp_url) if webapp_url else ''
                        # Ensure they are strings
                        openly_url = str(openly_url) if openly_url else ''
                        webapp_url = str(webapp_url) if webapp_url else ''
                    else:
                        openly_url = ''
                        webapp_url = ''
                    
                    # Ensure arrays are proper lists
                    keywords = metadata.get('keywords') or []
                    if not isinstance(keywords, list):
                        keywords = []
                    
                    constraints = metadata.get('constraints') or []
                    if not isinstance(constraints, list):
                        constraints = []
                    
                    document = {
                        "id": doc_id,
                        "content": searchable_text or "",
                        "title": metadata.get('title') or "",
                        "metauid": metadata.get('metauid') or "",
                        "data_type": metadata.get('data_type') or "",
                        "keywords": keywords,
                        "purpose": metadata.get('purpose') or "",
                        "abstract": metadata.get('abstract') or "",
                        "feature_type": metadata.get('feature_type') or "",
                        "service_type": metadata.get('service_type') or "",
                        "parent_metauid": metadata.get('parent_metauid') or "",
                        "constraints": constraints,
                        "openly_url": openly_url or "",
                        "webapp_url": webapp_url or "",
                        "datestamp": metadata.get('datestamp') or "",
                        "chunk_type": metadata.get('chunk_type') or 'main',
                        "content_vector": embedding
                    }
                    
                    documents_to_upload.append(document)
                
                # Upload in batches
                if len(documents_to_upload) >= batch_size:
                    success = self._upload_batch(search_client, documents_to_upload)
                    if not success:
                        stats['failed'] += len(documents_to_upload)
                    documents_to_upload = []
                
                # Small delay every 10 items to avoid rate limits
                if (idx + 1) % 10 == 0:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"⚠️  Error processing item {idx}: {e}")
                stats['failed'] += 1
                continue
        
        # Upload remaining documents
        if documents_to_upload:
            success = self._upload_batch(search_client, documents_to_upload)
            if not success:
                stats['failed'] += len(documents_to_upload)
        
        # Print statistics
        print("\n" + "="*80)
        print("✅ Indexing Complete!")
        print("="*80)
        print(f"📁 Collections indexed: {stats['collections']}")
        print(f"📊 Datasets indexed:    {stats['datasets']}")
        print(f"🔧 Services indexed:    {stats['services']}")
        print(f"📄 Other items:         {stats['other']}")
        print(f"📦 Total chunks:        {stats['chunks']}")
        print(f"❌ Failed:              {stats['failed']}")
        print(f"📈 Total items:         {sum([stats['collections'], stats['datasets'], stats['services'], stats['other']])}")
        print(f"⚡ Avg chunks/item:     {stats['chunks']/(stats['collections']+stats['datasets']+stats['services']+stats['other']):.1f}")
        print("="*80)
    
    def _upload_batch(self, search_client: SearchClient, documents: List[Dict]) -> bool:
        """Upload a batch of documents to the search index"""
        try:
            # Remove @search.action from documents for direct upload
            clean_docs = []
            for doc in documents:
                clean_doc = {k: v for k, v in doc.items() if not k.startswith('@')}
                clean_docs.append(clean_doc)
            
            search_client.merge_or_upload_documents(documents=clean_docs)
            print(f"  ✓ Uploaded batch of {len(documents)} documents")
            return True
        except Exception as e:
            print(f"  ✗ Error uploading batch: {e}")
            print(f"     First doc ID: {documents[0].get('id', 'unknown') if documents else 'no docs'}")
            return False


def main():
    """Main execution function"""
    print("="*80)
    print("State-of-the-Art Geopard RAG Setup (2025)")
    print("="*80)
    print("\nFeatures:")
    print("  🚀 text-embedding-3-large (3072-dim)")
    print("  🎯 Azure AI Search semantic ranking")
    print("  📚 Advanced chunking with overlap")
    print("  ⚡ Optimized HNSW parameters\n")
    
    rag = StateOfTheArtGeopardRAG()
    
    if rag.create_search_index():
        print("\n🚀 Starting indexing process...")
        rag.process_and_index_items("data/products_ktlu.json", batch_size=100)
        print("\n✅ Setup complete! You can now query the RAG system.")
    else:
        print("\n❌ Failed to create index. Please check your Azure credentials.")


if __name__ == "__main__":
    main()
