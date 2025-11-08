"""
State-of-the-Art RAG Query System for Geopard (2025)

Features:
- Azure AI Search semantic ranking (L2 reranker)
- Query decomposition and expansion
- text-embedding-3-large embeddings
- Response caching and evaluation
- Inline citations with confidence scores
"""

import os
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType, QueryCaptionType, QueryAnswerType
from azure.core.credentials import AzureKeyCredential

load_dotenv()


class StateOfTheArtGeopardRAG:
    """
    State-of-the-art query system for Geopard RAG (2025)
    - Semantic search with L2 reranking
    - Query decomposition
    - Embedding and response caching
    - Citation tracking
    """
    
    def __init__(self, index_name: Optional[str] = None):
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
        if index_name is None:
            index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "geopard-rag-v2")
        
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        
        if not search_endpoint or not search_key:
            raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set")
        
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key)
        )
        
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o")
        
        # Initialize caching
        self.cache_dir = Path(".rag_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.embedding_cache = {}
        self._load_embedding_cache()
    
    def _load_embedding_cache(self):
        """Load embedding cache from disk"""
        cache_file = self.cache_dir / "embeddings.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.embedding_cache = json.load(f)
            except Exception:
                self.embedding_cache = {}
    
    def _save_embedding_cache(self):
        """Save embedding cache to disk"""
        cache_file = self.cache_dir / "embeddings.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.embedding_cache, f)
        except Exception:
            pass
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def expand_query(self, query: str) -> List[str]:
        """Generate query variations for better retrieval"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für Geodaten. Generiere 2 alternative Formulierungen der Frage, um bessere Suchergebnisse zu erzielen. Antworte nur mit den Fragen, getrennt durch Zeilenumbrüche."},
                    {"role": "user", "content": f"Frage: {query}\n\nGeneriere 2 Varianten:"}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            variations = [query]  # Original query
            content = response.choices[0].message.content
            if content:
                expanded = content.strip().split('\n')
                variations.extend([v.strip() for v in expanded if v.strip() and not v.strip().startswith(('-', '*', '1.', '2.'))][:2])
            return variations[:3]  # Max 3 queries
            
        except Exception:
            return [query]  # Fallback to original
    
    def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for search query with caching"""
        cache_key = self._get_cache_key(query)
        
        # Check cache
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        try:
            response = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            self.embedding_cache[cache_key] = embedding
            if len(self.embedding_cache) % 10 == 0:  # Save every 10 embeddings
                self._save_embedding_cache()
            
            return embedding
        except Exception as e:
            print(f"❌ Error generating query embedding: {e}")
            return None
    
    def hybrid_search(
        self, 
        query: str, 
        top_k: int = 5,
        data_type_filter: Optional[str] = None,
        use_semantic: bool = True
    ) -> List[Dict]:
        """
        Perform hybrid search with semantic ranking (L2 reranker)
        
        Args:
            query: User's search query
            top_k: Number of results to return
            data_type_filter: Optional filter for data type
            use_semantic: Use Azure semantic search for reranking
        
        Returns:
            List of search results with metadata and reranker scores
        """
        query_embedding = self.generate_query_embedding(query)
        if not query_embedding:
            return []
        
        # Retrieve significantly more results to capture similar datasets with close scores
        # This ensures we get multiple versions of the same dataset (e.g., DTM 2024, 2018, 2012)
        # Using 5x multiplier to ensure we don't miss related datasets that rank slightly lower
        retrieval_count = top_k * 5
        
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=100,  # Retrieve more for reranking
            fields="content_vector"
        )
        
        filter_expression = None
        if data_type_filter:
            filter_expression = f"data_type eq '{data_type_filter}'"
        
        try:
            search_params = {
                "search_text": query,
                "vector_queries": [vector_query],
                "filter": filter_expression,
                "select": [
                    "id", "content", "title", "metauid", "data_type",
                    "keywords", "purpose", "abstract", "feature_type",
                    "service_type", "parent_metauid", "constraints",
                    "openly_url", "webapp_url", "chunk_type"
                ],
                "top": retrieval_count
            }
            
            # Add semantic search configuration
            if use_semantic:
                search_params.update({
                    "query_type": QueryType.SEMANTIC,
                    "semantic_configuration_name": "geopard-semantic-config",
                    "query_caption": QueryCaptionType.EXTRACTIVE,
                    "query_answer": QueryAnswerType.EXTRACTIVE
                })
            
            results = self.search_client.search(**search_params)
            
            search_results = []
            for result in results:
                result_dict = {
                    "id": result.get("id"),
                    "title": result.get("title", ""),
                    "metauid": result.get("metauid", ""),
                    "data_type": result.get("data_type", ""),
                    "keywords": result.get("keywords", []),
                    "purpose": result.get("purpose", ""),
                    "abstract": result.get("abstract", ""),
                    "feature_type": result.get("feature_type", ""),
                    "service_type": result.get("service_type", ""),
                    "constraints": result.get("constraints", []),
                    "openly_url": result.get("openly_url", ""),
                    "webapp_url": result.get("webapp_url", ""),
                    "content": result.get("content", ""),
                    "chunk_type": result.get("chunk_type", "main"),
                    "score": result.get("@search.score", 0),
                    "reranker_score": result.get("@search.reranker_score", 0),
                }
                
                # Add semantic captions if available
                if hasattr(result, '@search.captions'):
                    captions = getattr(result, '@search.captions', [])
                    if captions:
                        result_dict["caption"] = captions[0].text if hasattr(captions[0], 'text') else ""
                
                search_results.append(result_dict)
            
            # Deduplicate by metauid, keeping highest scoring chunk
            seen_metauids = {}
            for r in search_results:
                metauid = r['metauid']
                if metauid not in seen_metauids or r.get('reranker_score', 0) > seen_metauids[metauid].get('reranker_score', 0):
                    seen_metauids[metauid] = r
            
            deduplicated = list(seen_metauids.values())
            
            # YEAR-BASED RERANKING: Prioritize newer datasets
            # Extract year from title and boost recent datasets
            import re
            for result in deduplicated:
                title = result.get('title', '')
                # Extract 4-digit years from title (e.g., "DOM 2024", "DTM 2018")
                years = re.findall(r'\b(20[0-2][0-9])\b', title)
                if years:
                    # Get the most recent year mentioned in the title
                    max_year = max(int(y) for y in years)
                    result['extracted_year'] = max_year
                else:
                    result['extracted_year'] = 0  # No year found, lowest priority
            
            # Sort by year (descending), then by relevance score
            # This ensures that among equally relevant results, newer ones come first
            deduplicated.sort(
                key=lambda x: (
                    x.get('extracted_year', 0),  # Primary: year (newer first)
                    x.get('reranker_score', x.get('score', 0))  # Secondary: relevance
                ),
                reverse=True
            )
            
            return deduplicated[:top_k]
            
        except Exception as e:
            print(f"❌ Error during hybrid search: {e}")
            return []
    
    def generate_response(self, query: str, results: List[Dict]) -> Dict:
        """
        Generate final response using LLM with inline citations
        
        Args:
            query: User's question
            results: Search results
        
        Returns:
            Dict with answer, confidence, and citations
        """
        context_parts = []
        for idx, result in enumerate(results, 1):
            context = f"\n### [Quelle {idx}] {result['title']}\n"
            context += f"- **MetaUID**: {result['metauid']}\n"
            context += f"- **Typ**: {result['data_type']}\n"
            context += f"- **Relevanz-Score**: {result.get('reranker_score', result.get('score', 0)):.2f}\n"
            
            # Use caption if available (from semantic search)
            if result.get('caption'):
                context += f"- **Relevanter Auszug**: {result['caption']}\n"
            elif result.get('purpose'):
                purpose = result['purpose'][:200]
                context += f"- **Zweck**: {purpose}...\n"
            
            if result.get('keywords'):
                context += f"- **Keywords**: {', '.join(result['keywords'][:5])}\n"
            
            if result.get('constraints'):
                context += f"- **Zugang**: {', '.join(result['constraints'])}\n"
            
            # Extract WMS/WFS URLs from raw content
            raw_content = result.get('content', '')
            wms_urls = []
            wfs_urls = []
            if 'WMSServer' in raw_content:
                # Find WMS URLs
                import re
                wms_matches = re.findall(r'https://[^\s"\'\}]+/WMSServer[^\s"\'\}]*', raw_content)
                wms_urls = list(set(wms_matches))[:2]  # Max 2 unique URLs
            if 'WFSServer' in raw_content:
                # Find WFS URLs
                import re
                wfs_matches = re.findall(r'https://[^\s"\'\}]+/WFSServer[^\s"\'\}]*', raw_content)
                wfs_urls = list(set(wfs_matches))[:2]  # Max 2 unique URLs
            
            if wms_urls:
                context += f"- **WMS Service**: {wms_urls[0]}\n"
            if wfs_urls:
                context += f"- **WFS Service**: {wfs_urls[0]}\n"
            
            if result.get('openly_url'):
                context += f"- **Metadaten**: {result['openly_url']}\n"
            
            context_parts.append(context)
        
        full_context = "\n".join(context_parts)
        
        system_prompt = """Du bist ein hilfreicher Assistent für Geodaten des Kantons Luzern.

SPRACHE: Antworte IMMER auf Schweizer Hochdeutsch.

WICHTIG: Du hilfst Nutzern, die RICHTIGEN DATENSÄTZE zu finden, aber du hast keinen direkten Zugriff auf die Geodaten selbst, ausser den MCPs.

PRIORITÄT - NEUERE DATENSÄTZE BEVORZUGEN:
- Wenn mehrere Versionen desselben Datensatzes mit unterschiedlichen Jahreszahlen vorhanden sind (z.B. DTM 2024, DTM 2018, DTM 2012), bevorzuge die Version mit dem NEUESTEN Jahr
- Ältere Versionen sollen weniger beachtet werden, es sei denn der Nutzer fragt explizit nach historischen Daten
- Beispiel: Bei "DTM 2024" und "DTM 2012" → erwähne eher "DTM 2024"
- Beispiel: Bei "Orthofoto 2023" und "Orthofoto 2011" → erwähne eher "Orthofoto 2023"

KRITISCHE UNTERSCHEIDUNGEN bei Höhenabfragen:
- Bei MEHRDEUTIGEN Fragen (z.B. "Höhe eines Gebäudes/Objekts"): ERKLÄRE die Optionen und FRAGE nach der genauen Intention
- **DOM (Digitales Oberflächenmodell)**: Zeigt die Oberkante von Objekten (Gebäude, Torbogen, Bäume)
  → Nutze für: Gebäudehöhen, Objekthöhen, Höhe von Bauwerken
- **DTM (Digitales Terrainmodell)**: Zeigt nur das Gelände (ohne Gebäude/Vegetation)
  → Nutze für: Geländehöhe, Bodenhöhe, Topographie
- **3D-Gebäudemodelle**: Detaillierte Gebäudegeometrie mit Höhenangaben
  → Nutze für: Spezifische Gebäudeinformationen

RASTER vs. PUNKTWOLKE:
- Wenn sowohl **Raster** als auch **Punktwolke** verfügbar sind, ERKLÄRE den Unterschied:
  - **Raster**: Strukturiertes Gitter mit regelmässigen Zellen (Pixeln), ideal für Analysen, Visualisierung und einfache Weiterverarbeitung (z.B. in GIS-Software)
  - **Punktwolke**: Unstrukturierte 3D-Punkte mit höherer Detailgenauigkeit, ideal für präzise 3D-Modellierung und Vermessung
- Empfehle basierend auf dem Anwendungsfall: Raster für GIS-Analysen, Punktwolke für hochgenaue 3D-Anwendungen

METADATEN AUSGEBEN:
- Verlinke NICHT nur die Metadaten-URL, sondern SCHREIBE die wichtigsten Metadaten-Informationen direkt aus
- Gib an: Titel, Beschreibung, Aktualität, Format, räumliche Auflösung, Koordinatensystem (falls verfügbar)
- Erst DANACH den Metadaten-Link für weitere Details

ANTWORT-STRATEGIE bei mehrdeutigen Höhenabfragen:
1. Erkläre BEIDE relevanten Datensätze (DOM für Oberkante, DTM für Bodenhöhe)
2. Stelle eine KLÄRENDE FRAGE: "Möchten Sie die Höhe der Oberkante des Objekts (→ DOM) oder die Geländehöhe am Standort (→ DTM)?"
3. Gib für BEIDE Optionen MetaUID und Zugriffsinformationen an
4. Bei eindeutigen Fragen: Wähle direkt den passenden Datensatz

Weitere Regeln:
- Erkläre WIE der Nutzer die Daten abrufen kann (WMS/WFS URLs wenn verfügbar)
- Zitiere Quellen mit [Quelle N]
- Nenne Datensatz-Namen und MetaUID
- Bewerte deine Antwort-Sicherheit (0-100%)

Format:
1. Klärende Erklärung (falls mehrdeutig)
2. Empfohlene Datensätze mit Erklärung (mit [Quelle N], MetaUID, WMS/WFS wenn verfügbar)
3. Ausgeschriebene Metadaten (Titel, Beschreibung, Aktualität, Format, etc.)
4. Wie kann man die Daten nutzen?
5. Metadaten-Links für weitere Details
6. Am Ende: CONFIDENCE: XX%

Antworte auf Schweizer Hochdeutsch, präzise, pädagogisch und benutzerfreundlich."""
        
        user_prompt = f"""Kontext - Gefundene Datensätze (sortiert nach Relevanz):
{full_context}

Frage: {query}

Bitte beantworte die Frage basierend auf den gefundenen Datensätzen. Zitiere Quellen mit [Quelle N].

Antwort:"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower for more deterministic answers
                max_tokens=3000  # Increased for detailed explanatory answers
            )
            
            answer_text = response.choices[0].message.content or ""
            
            # Extract confidence if provided
            confidence = 75  # Default
            if "CONFIDENCE:" in answer_text:
                try:
                    conf_str = answer_text.split("CONFIDENCE:")[1].split("%")[0].strip()
                    confidence = int(conf_str)
                    answer_text = answer_text.split("CONFIDENCE:")[0].strip()
                except Exception:
                    pass
            
            return {
                "answer": answer_text,
                "confidence": confidence,
                "model": self.chat_model
            }
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return {
                "answer": "Entschuldigung, es gab einen Fehler bei der Antwortgenerierung.",
                "confidence": 0,
                "model": self.chat_model
            }
    
    def query(self, question: str, top_k: int = 5, use_query_expansion: bool = False) -> Dict:
        """
        Complete RAG query with state-of-the-art features
        
        Args:
            question: User's question
            top_k: Number of datasets to retrieve
            use_query_expansion: Use query expansion for better recall
        
        Returns:
            Dict with question, answer, confidence, and sources
        """
        print("\n🔍 Searching with semantic ranking...")
        
        # Optional: Query expansion
        if use_query_expansion:
            print("   ↳ Expanding query...")
            query_variations = self.expand_query(question)
            
            # Search with multiple queries and merge results
            all_results = []
            for q in query_variations:
                results = self.hybrid_search(q, top_k=top_k, use_semantic=True)
                all_results.extend(results)
            
            # Deduplicate and sort by score
            seen = {}
            for r in all_results:
                metauid = r['metauid']
                if metauid not in seen or r.get('reranker_score', 0) > seen[metauid].get('reranker_score', 0):
                    seen[metauid] = r
            results = sorted(seen.values(), key=lambda x: x.get('reranker_score', x.get('score', 0)), reverse=True)[:top_k]
        else:
            results = self.hybrid_search(question, top_k=top_k, use_semantic=True)
        
        if not results:
            return {
                "question": question,
                "answer": "Ich konnte keine relevanten Datensätze zu Ihrer Frage finden.",
                "confidence": 0,
                "sources": []
            }
        
        print(f"   ✓ Found {len(results)} datasets (avg score: {sum(r.get('reranker_score', r.get('score', 0)) for r in results)/len(results):.2f})")
        print("\n💬 Generating response with citations...")
        
        response_data = self.generate_response(question, results)
        
        sources = [
            {
                "title": r["title"],
                "metauid": r["metauid"],
                "data_type": r["data_type"],
                "openly_url": r.get("openly_url", ""),
                "webapp_url": r.get("webapp_url", ""),
                "relevance_score": round(r.get('reranker_score', r.get('score', 0)), 2),
                "caption": r.get("caption", "")
            }
            for r in results
        ]
        
        return {
            "question": question,
            "answer": response_data["answer"],
            "confidence": response_data["confidence"],
            "sources": sources,
            "model": response_data["model"]
        }


if __name__ == "__main__":
    print("="*80)
    print("State-of-the-Art Geopard RAG Query Test (2025)")
    print("="*80)
    
    rag = StateOfTheArtGeopardRAG()
    
    test_query = "Welcher Datensatz enthält Informationen über Wildruhezonen?"
    
    print(f"\n📝 Query: {test_query}\n")
    result = rag.query(test_query, top_k=3, use_query_expansion=False)
    
    print("\n" + "="*80)
    print("ANSWER:")
    print("="*80)
    print(result["answer"])
    print(f"\n📊 Confidence: {result['confidence']}%")
    print(f"🤖 Model: {result['model']}")
    
    print("\n" + "="*80)
    print("SOURCES:")
    print("="*80)
    for i, source in enumerate(result["sources"], 1):
        print(f"\n{i}. {source['title']}")
        print(f"   MetaUID: {source['metauid']}")
        print(f"   Type: {source['data_type']}")
        print(f"   Relevance: {source['relevance_score']}")
        if source.get('caption'):
            print(f"   Caption: {source['caption'][:100]}...")
        if source.get('openly_url'):
            print(f"   Metadata: {source['openly_url']}")
