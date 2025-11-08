"""
Interactive query interface for State-of-the-Art Geopard RAG (2025)
"""

from rag_query import StateOfTheArtGeopardRAG
import sys


def print_header():
    """Print welcome header"""
    print("\n" + "="*80)
    print(" 🗺️  GEOPARD RAG 2025 - State-of-the-Art Geodaten-Assistent")
    print("="*80)
    print("\n ✨ Features:")
    print("   • Azure AI Search Semantic Ranking (L2 Reranker)")
    print("   • text-embedding-3-large (3072-dim)")
    print("   • Query Expansion & Caching")
    print("   • Inline Citations & Confidence Scores\n")
    print("-"*80)


def print_help():
    """Print help message"""
    print("\n📚 Befehle:")
    print("  'quit' oder 'exit' - Programm beenden")
    print("  'help' - Diese Hilfe anzeigen")
    print("  'examples' - Beispielfragen anzeigen")
    print()


def print_examples():
    """Print example queries"""
    print("\n💡 Beispielfragen:")
    print()
    print("  1. Welcher Datensatz enthält Informationen über Wildruhezonen?")
    print()
    print("  2. Wo finde ich Daten zur amtlichen Vermessung?")
    print()
    print("  3. Welche Datensätze gibt es zu Oberflächengewässern?")
    print()
    print("  4. Ich suche Höhendaten für den Kanton Luzern")
    print()
    print("  5. Gibt es Lärmbelastungsdaten für Gebäude?")
    print()
    print("-"*80)


def format_response(result: dict):
    """Format and display the response"""
    print("\n" + "="*80)
    print("💬 ANTWORT:")
    print("="*80)
    print()
    print(result['answer'])
    
    # Show confidence score
    if result.get('confidence'):
        confidence = result['confidence']
        conf_emoji = "🟢" if confidence >= 80 else "🟡" if confidence >= 60 else "🔴"
        print(f"\n{conf_emoji} Confidence: {confidence}%")
    
    if result.get('sources'):
        print("\n" + "="*80)
        print(f"📚 QUELLEN ({len(result['sources'])} Datensätze):")
        print("="*80)
        
        for i, source in enumerate(result['sources'], 1):
            print(f"\n{i}. {source['title']}")
            print(f"   └─ MetaUID: {source['metauid']}")
            print(f"   └─ Typ: {source['data_type']}")
            print(f"   └─ Relevanz: {source.get('relevance_score', 0)}")
            
            if source.get('caption'):
                print(f"   └─ 📝 {source['caption'][:150]}...")
            
            if source.get('openly_url'):
                print(f"   └─ 📄 Metadaten: {source['openly_url']}")
    
    print("\n" + "="*80)


def main():
    """
    Interactive query loop
    """
    print_header()
    
    print("🔄 System wird initialisiert...")
    
    try:
        rag = StateOfTheArtGeopardRAG()
        print("✅ System bereit!\n")
    except Exception as e:
        print(f"\n❌ Fehler beim Initialisieren: {e}")
        print("\nBitte überprüfen Sie:")
        print("  1. Die .env Datei mit Azure Credentials existiert")
        print("  2. Der RAG-Index wurde mit rag_setup.py erstellt")
        sys.exit(1)
    
    print_help()
    print("Geben Sie 'examples' ein, um Beispielfragen zu sehen.")
    print("-"*80)
    
    query_count = 0
    
    while True:
        try:
            query = input("\n🔍 Ihre Frage: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Auf Wiedersehen!")
                print(f"📊 Sie haben {query_count} Fragen gestellt.\n")
                break
            
            if query.lower() == 'help':
                print_help()
                continue
            
            if query.lower() in ['examples', 'beispiele']:
                print_examples()
                continue
            
            print("\n⏳ Suche läuft (mit semantic reranking)...")
            result = rag.query(query, top_k=5, use_query_expansion=False)
            query_count += 1
            
            format_response(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 Auf Wiedersehen!")
            print(f"📊 Sie haben {query_count} Fragen gestellt.\n")
            break
            
        except Exception as e:
            print(f"\n❌ Fehler: {e}")
            print("Bitte versuchen Sie es erneut oder geben Sie 'help' ein.\n")


if __name__ == "__main__":
    main()
