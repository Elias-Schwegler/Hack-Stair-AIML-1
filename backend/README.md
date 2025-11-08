# RAG v2

Semantic search + Q&A over ~500 geodata datasets using Azure AI Search + GPT-4o.

**Features**: Hybrid search (vector + keyword) • L2 semantic ranking • Inline citations • Confidence scores • German-optimized

## Setup

```bash
# Configure .env in project root, then:
python rag_setup.py          # Create index (~10-15 min)
python interactive_query.py  # Start querying
```

## Usage

```python
from rag_query import StateOfTheArtGeopardRAG

rag = StateOfTheArtGeopardRAG()
result = rag.query("Welche Höhendaten gibt es?", top_k=5)

print(result['answer'])      # Answer with [Quelle N] citations
print(result['confidence'])  # 0-100%
print(result['sources'])     # Source datasets
```

**Performance**: Search ~200-500ms • First query ~2-3s • Cached queries ~500ms-2s
