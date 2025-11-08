# Architekturübersicht — Geoportal Chatbot

Dieses Dokument beschreibt auf hoher Ebene, wie Daten für den Chatbot beschafft und verarbeitet werden.
Die Beschreibung und das Diagramm sind auf Deutsch gehalten (wie gewünscht).

--------------------------------------------------------------------------------

ASCII-Architektur (hoch-level)

 +-------------+        +-----------------+        +----------------------+ 
 |  Frontend   | <----> |   Backend /     | <----> |   Services / APIs    | 
 | (index.html)|        |   FastAPI App   |        |                      | 
 +-------------+        +-----------------+        +----------------------+ 
                           |     |    |  
                           |     |    +--> Azure OpenAI (Chat + Embeddings)
                           |     +------> Azure Cognitive Search (Index)
                           +------------> LocationService / GeoService (extra metadata)

                               ^
                               |
                         Data / Indexing pipeline
                               |
                 +-------------------------------+
                 |   Ingestion & Preprocessing   |
                 |  - local JSON / CSV           |
                 |  - cleaning / metadata        |
                 |  - embeddings (text-embedding)|
                 |  - index -> Azure Search     |
                 +-------------------------------+

--------------------------------------------------------------------------------

High-level Datenfluss (Schritte)

1) Ingestion
   - Quelldaten: lokale Dateien (`backend/data/products_ktlu.json`), evtl. weitere Quellen.
   - Skripte: `backend/recreate_index.py` etc. lesen, transformieren und bereiten Dokumente vor.

2) Embeddings & Indexing
   - Texte werden in Vektoren konvertiert (z. B. `text-embedding-3-large`).
   - Vektoren und relevante Metadaten (Titel, URL, Thema, Geocoordinates) werden in Azure Cognitive Search indexiert.

3) Query / Laufzeit (User-Interaktion)
   - Frontend sendet User-Message an Backend `POST /chat`.
   - Backend erzeugt Embedding der User-Message (Embedding-API) oder nutzt OpenAI-Service.
   - Semantic Search (kNN) gegen Azure Search -> Top-K relevante Dokumente werden abgerufen.
   - Prompt Construction: Templates fügen System-Message, relevante Dokumentausschnitte und Konversationshistorie zusammen.
   - Chat-API (Azure OpenAI) erzeugt Antwort (RAG-Pattern: Retrieval-Augmented Generation).
   - Antwort wird an Frontend zurückgegeben; Konversationshistorie wird optional erweitert/gespeichert.

4) Zusätzliche Hilfsservices
   - LocationService / GeoService: nutzt Metadaten (Koordinaten) für räumliche Abfragen, ggf. Reverse-Geocoding.
   - Monitoring & Health: `/health`-Endpoint prüft Verbindung zu Azure-Services.

--------------------------------------------------------------------------------

Wichtige Komponenten und Dateien in diesem Repo

- `frontend/index.html` — einfache Web-UI, kommuniziert mit `POST /chat`.
- `backend/main.py` — FastAPI-Anwendung, Endpoints (`/`, `/chat`, `/health`, `/stats`).
- `backend/services/azure_openai_service.py` — Abstraktion für Chat- und Embedding-Aufrufe.
- `backend/services/azure_search_service.py` — Wrapper für Azure Cognitive Search.
- `backend/recreate_index.py` — Skript zum Erzeugen/Neuaufbau des Suchindex.
- `backend/data/` — Beispieldatenquellen (z. B. `products_ktlu.json`).
- `.env` — Konfiguration (Azure Keys, Endpoints, Model-/Deploymentnamen).

--------------------------------------------------------------------------------

Design- und Betriebsnotizen

- Host/Port: Backend läuft als FastAPI/Uvicorn-Service. In Browser immer `http://localhost:<port>` öffnen (nicht 0.0.0.0).
- Sicherheit: API-Keys liegen in `.env` — niemals in ein öffentliches Repository pushen.
- Kosten: Embedding- und Chat-Aufrufe sind kostenpflichtig; achte auf Batch-Größen und Token-Nutzung.

Frontend-Serving (häufige Fragen)

- Standardverhalten: Der Backend-Server liefert standardmäßig die API-Endpoints (JSON). `GET /` kann JSON zurückgeben oder, falls konfiguriert, das `frontend/index.html` ausliefern. Wenn du nur JSON siehst (wie zuvor), dann lief der Server ohne statische Frontend-Auslieferung.
- Zwei einfache Möglichkeiten, das Frontend zu sehen:
   1) Direkt öffnen: Datei `frontend/index.html` im Browser öffnen (lokal, kein Server nötig).
   2) Kleiner HTTP-Server (Repo-Root):
       - PowerShell:
          ```powershell
          cd C:\path\to\repo\frontend
          python -m http.server 8000
          Start-Process http://localhost:8000
          ```
   3) Vom Backend servieren: Wenn `backend/main.py` statische Dateien mountet (z. B. mit `StaticFiles`), wird `http://localhost:<port>/` die UI liefern. Andernfalls liefert der Backend-Root JSON.

- 0.0.0.0 vs localhost: `0.0.0.0` ist ein Bind-Host (zeigt "auf allen Netzwerk-Interfaces lauschen"), aber im Browser solltest du `http://localhost:<port>` oder `http://127.0.0.1:<port>` verwenden. `http://0.0.0.0:<port>/` ist kein gültiger URL für Browser (führt zu ERR_ADDRESS_INVALID).

Konkrete Run-/Start-Beispiele (Windows PowerShell)

- Standard: Backend aus dem Repo-Root als Modul starten (importpfad korrekt):
   ```powershell
   cd C:\Users\elias\Documents\HackStair_Rotkreuz\GIT\Hack-Stair-AIML-1
   python -m backend.main
   ```

- Port ändern temporär (nur für die aktuelle PowerShell-Session):
   ```powershell
   $env:PORT = "8888"
   python -m backend.main
   Start-Process http://localhost:8888
   ```

- Direkter uvicorn-Start (mehr Kontrolle):
   ```powershell
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8888
   Start-Process http://localhost:8888
   ```

Hinweis: Firewall oder andere Sicherheitseinstellungen können Zugriffe verhindern; prüfe die Windows-Firewall, falls extern von anderen Geräten nicht erreichbar.

--------------------------------------------------------------------------------

Verbesserungsideen für Chat-Antworten (nächste Schritte)

1) Prompt-Engineering
   - Definiere einen starken System-Prompt (Deutsch), der Ton, Kürze/Länge, Quellenangaben, Zitierformat vorgibt.
   - Erstelle Prompt-Templates mit Platzhaltern: {system}, {user}, {context_docs}, {history}.

2) Retrieval-Optimierung
   - Re-Ranking: Nachsemantischer Suche eine Relevanz-Rerank-Phase (BM25/other) einbauen.
   - Metadaten-Filter: geografische filter, Datum, Dokumenttyp zur Verbesserung der Treffergenauigkeit.

3) Antwortqualität
   - Quellenangaben: immer die Quelle(n) der Retrieval-Dokumente hinzufügen (z. B. Titel + URL).
   - Kurzantwort + optionaler ausführlicher Abschnitt (falls User nach mehr fragt).
   - Fallback-Strategie: Wenn keine relevanten Dokumente, explizit sagen: "Dafür habe ich keine Dokumentation gefunden" und Vorschläge anbieten.

4) Sprache & Stil
   - Erkenne Sprache automatisch und setze System-Prompt auf Deutsch, wenn Deutsch erkannt.
   - Stelle Fachvokabular präzise dar (Domain-specific glossar als Referenz möglich).

5) Tests
   - Minimal-Integrationstest für `/chat` (happy path + fallback path).
   - Unit-Tests für Prompt-Builder und Retrieval-Pipeline.

--------------------------------------------------------------------------------

Vertrag (klein) — Input/Output Erwartungen

- Input: User-Message (Text), optionale `conversation_history` (Liste von {role, content}).
- Output: JSON { response: str, conversation_history: [...] } mit Quellen-Metadaten im response oder als separate Felder.
- Fehler: Bei internen Fehlern HTTP 500 mit kurzer Fehlermeldung; Health-Endpoint liefert Verbindungsstatus.

--------------------------------------------------------------------------------

Edge Cases

- Leere Anfrage: valide Antwort mit Hinweis "Bitte stellen Sie eine Frage".
- Keine Treffer aus Retrieval: freundlich darauf hinweisen, alternative Formulierungen vorschlagen.
- Langsame API / Zeitüberschreitung: Timeout-Handling und Fallback-Meldung.

--------------------------------------------------------------------------------

Was ich als Nächstes tun kann

- (optional) Das Backend so erweitern, dass `GET /` das Frontend liefert (falls gewünscht).
- Prompt-Template-Datei hinzufügen und Beispielsystemprompt in Deutsch implementieren.
- Kleine Unit-Tests für Prompt-Builder und Health-Check.

Wenn du möchtest, starte ich mit einem deutschsprachigen System-Prompt und einem Prompt-Template, das wir in `backend/services/azure_openai_service.py` einbinden können.
