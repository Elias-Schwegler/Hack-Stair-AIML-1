# 🌍 Geopard Web Server - Schnellstart-Anleitung

## ✅ Was wurde implementiert

Der Webserver nutzt jetzt **vollständig MCP (Model Context Protocol)** mit folgenden Features:

### 🎯 Kernfunktionalität

1. **MCP-Tool-Integration** - Alle Geodaten-Tools als OpenAI Functions
2. **Intelligente Orchestrierung** - LLM entscheidet automatisch über Tool-Nutzung
3. **Multi-Turn Conversations** - Konversationsverläufe werden berücksichtigt
4. **Production-Ready** - Umfassendes Start-Skript mit Validierung

### 🔧 Verfügbare Tools

- ✅ `search_geodata_datasets` - Semantische Datensatz-Suche (RAG)
- ✅ `ask_geodata_question` - KI-generierte Antworten mit Zitaten
- ✅ `search_location` - Location Finder (Adressen, EGID, etc.)
- ✅ `create_map_link` - Interaktive Karten-URLs

---

## 🚀 Schnellstart in 3 Schritten

### 1️⃣ Environment konfigurieren

```bash
# Ins Projekt-Verzeichnis wechseln
cd /home/david/HackSTAIR2025/git/Hack-Stair-AIML-1

# .env Datei erstellen (falls nicht vorhanden)
cp .env.example .env

# Azure Credentials eintragen
nano .env  # oder bevorzugten Editor nutzen
```

**Erforderliche Credentials:**
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_KEY`

### 2️⃣ Server starten

```bash
# Einfach starten (Port 8000)
./start_server.sh

# Mit Optionen
./start_server.sh --port 8080        # Anderen Port
./start_server.sh --dev              # Development-Modus
./start_server.sh --help             # Hilfe
```

Das Skript führt automatisch aus:
- ✅ Python-Version prüfen
- ✅ Virtual Environment erstellen/aktivieren
- ✅ Dependencies installieren
- ✅ Azure-Verbindungen testen
- ✅ Port freigeben (falls belegt)
- ✅ Server starten

### 3️⃣ Testen

```bash
# Health Check
curl http://localhost:8000/health

# Tool Liste
curl http://localhost:8000/tools

# Chat UI öffnen
# Browser: http://localhost:8000
```

---

## 📁 Dateistruktur

```
frontend/
├── chat_server_mcp.py       # ✨ NEUER MCP-Server (verwenden!)
├── chat_server.py            # Alter Server (deprecated)
├── index.html                # Chat UI
├── chat.js                   # Frontend-Logik
├── map.js                    # Karten-Integration
├── styles.css                # Styling
├── MCP_INTEGRATION.md        # Detaillierte Dokumentation
└── README.md                 # Diese Datei

/ (Projekt-Root)
├── start_server.sh           # ✨ Start-Skript
├── .env.example              # Environment-Template
├── .env                      # Deine Credentials (nicht committen!)
├── requirements.txt          # Python Dependencies
├── mcp_server.py             # Standalone MCP Server
└── backend/                  # RAG System
    ├── rag_query.py
    └── ...
```

---

## 🔍 Wie MCP funktioniert

### Alter Ansatz (chat_server.py)

```python
# Direkte RAG-Abfrage - limitiert
result = rag_system.query(user_message)
return result['answer']
```

❌ **Probleme:**
- Nur RAG, keine anderen Tools
- Keine Location-Integration
- Keine intelligente Orchestrierung

### Neuer Ansatz (chat_server_mcp.py)

```python
# LLM entscheidet über Tool-Nutzung
response = openai.chat.completions.create(
    messages=conversation,
    tools=mcp_tools,        # Alle verfügbaren Tools
    tool_choice="auto"      # Automatische Auswahl
)

# Automatisches Tool Chaining
if response.tool_calls:
    # Execute tools → LLM nutzt Ergebnisse → Finale Antwort
```

✅ **Vorteile:**
- Mehrere Tools kombinierbar
- Intelligente Auswahl durch LLM
- Multi-Step Reasoning
- Bessere Antwortqualität

---

## 💡 Beispiel: Tool Chaining

**User:** "Zeige mir Höhendaten in Luzern auf einer Karte"

**Server-Ablauf:**

1. **LLM analysiert** → Benötigt: Datensatz + Location + Map
2. **Tool 1:** `search_geodata_datasets("Höhendaten")`
   - Ergebnis: DOM und DTM Datensätze
3. **Tool 2:** `search_location("Luzern")`
   - Ergebnis: Koordinaten (2666000, 1211000)
4. **Tool 3:** `create_map_link(theme="hoehen", x=2666000, y=1211000)`
   - Ergebnis: https://geo.lu.ch/map/?...
5. **LLM generiert Antwort:**
   ```
   Für Höhendaten in Luzern gibt es zwei Hauptdatensätze:
   
   1. DOM (Digitales Oberflächenmodell) - MetaUID: 2f2c3...
      Zeigt die Oberkante inklusive Gebäude
   
   2. DTM (Digitales Terrainmodell) - MetaUID: 8b4a1...
      Zeigt das reine Gelände
   
   Hier sehen Sie die Daten auf der Karte: [Link]
   ```

---

## 🏥 Health Monitoring

Der Server bietet umfassende Health Checks:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
    "status": "healthy",
    "rag_available": true,
    "mcp_available": true,
    "azure_openai": true,
    "azure_search": true
}
```

**Status-Werte:**
- `healthy` - Alle Systeme funktionieren
- `degraded` - Einige Systeme nicht verfügbar

---

## 🐛 Troubleshooting

### Problem: Server startet nicht

```bash
# Check Python
python3 --version  # Sollte >= 3.8 sein

# Check .env
cat .env  # Credentials korrekt?

# Manuelle Installation
source venv/bin/activate
pip install -r requirements.txt
pip install fastapi uvicorn mcp
```

### Problem: RAG nicht verfügbar

```bash
# Azure-Verbindung testen
cd backend
python3 test_hackathon_questions.py
```

### Problem: Port belegt

```bash
# Prozess finden und beenden
lsof -i :8000
kill -9 <PID>

# Oder anderen Port nutzen
./start_server.sh --port 8080
```

---

## 📊 Vergleich: Alt vs. Neu

| Feature | Alter Server | Neuer MCP Server |
|---------|-------------|------------------|
| RAG Suche | ✅ | ✅ |
| Location Finder | ❌ | ✅ |
| Karten-Integration | ❌ | ✅ |
| Tool Chaining | ❌ | ✅ |
| Konversation | Limitiert | ✅ Vollständig |
| Intelligenz | Fest programmiert | LLM-gesteuert |
| Erweiterbarkeit | Schwierig | Einfach (neue Tools) |

---

## 📚 Weitere Dokumentation

- **Detaillierte MCP-Doku:** `MCP_INTEGRATION.md`
- **RAG System:** `../backend/README.md`
- **Location Tools:** `../location-tools/README.md`
- **MCP Spec:** https://spec.modelcontextprotocol.io/

---

## 🎉 Los geht's!

```bash
# Server starten
./start_server.sh

# Browser öffnen
# → http://localhost:8000

# Erste Frage:
# "Welche Höhendaten gibt es im Kanton Luzern?"
```

**Viel Erfolg! 🚀**
