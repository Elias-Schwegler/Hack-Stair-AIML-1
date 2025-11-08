import os
import json
from typing import List, Dict, Optional
from openai import AzureOpenAI
import sys
import requests
import xml.etree.ElementTree as ET
sys.path.append('.')
from .azure_search_service import AzureSearchService
from .location_service import LocationService

class AzureOpenAIService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-08-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        # Initialize other services
        self.search_service = AzureSearchService()
        self.location_service = LocationService()
    
    def _get_system_prompt(self) -> str:
        return """Du bist ein hilfsbereiter Assistent für das Geoportal des Kantons Luzern.
        Deine Aufgaben:
        1. Helfe Nutzern, die richtigen Geodatensätze zu finden
        2. Beantworte Fragen zu Geodaten und deren Metadaten
        3. Finde Standorte und verlinke zu passenden Karten
        4. Gib immer die Quellen (URLs zu Metadaten und Geodatashop) an

        Verfügbare Tools:
        - search_metadata: Suche nach Geodatensätzen in der Metadatenbank
        - resolve_location: Finde Koordinaten für Adressen, Orte, Gebäude (EGID), Grundstücke (EGRID)
        - generate_map_url: Erstelle Links zu interaktiven Webkarten mit Marker

        WICHTIG - Wann welches Tool verwenden:
        - Bei Fragen nach "Welcher Datensatz..." → search_metadata verwenden
        - Bei Fragen nach "Wo liegt..." oder "Auf welcher Höhe..." → ZUERST resolve_location, DANN search_metadata für passende Daten, DANN generate_map_url
        - Bei Fragen nach "Informationen über..." → search_metadata verwenden

        Antwort-Format:
        - Gib immer konkrete Links zu Metadaten und Geodatashop an
        - Bei Standort-Fragen: Koordinaten nennen UND Webkarten-Link erstellen
        - Bei Höhenfragen: Erkläre, welcher Datensatz die Höhe zeigt (z.B. DTM) und wie man sie abrufen kann
        - Zitiere die Datenquellen klar

        Beispiele:
        Frage: "Auf welcher Höhe liegt der Bahnhof Luzern?"
        1. resolve_location("Bahnhof Luzern")
        2. search_metadata("Höhendaten Terrain DTM")
        3. generate_map_url mit den gefundenen Koordinaten
        Antwort: "Der Bahnhof Luzern liegt bei Koordinaten X: 2667123, Y: 1212345. Um die genaue Höhe abzufragen, nutze den Datensatz 'Digitales Terrainmodell (DTM)'. [Link zur Karte mit Marker]"

        Antworte auf Deutsch, präzise und hilfreich."""

    def _get_tools(self) -> List[Dict]:
        map_id = []
        url = "https://map.geo.lu.ch/feed.xml"
        r = requests.get(url, timeout=20)
        r.raise_for_status()

        root = ET.fromstring(r.content)

        links = []
        for item in root.findall(".//item/link"):
            link_text = item.text.strip()
            if "map.geo.lu.ch" in link_text:
                path = link_text.split("map.geo.lu.ch", 1)[1]
                links.append(path)

        for l in links:
            map_id.append(l)
        
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_metadata",
                    "description": "Suche nach Geodatensätzen und Collections in der Metadatenbank. Verwende dies für Fragen nach 'Welcher Datensatz...', 'Welche Daten...', 'Informationen über...'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Suchbegriff für Geodaten. Beispiele: 'Höhendaten DTM', 'Verkehrslärm', 'Gewässer See', 'Gebäude'"
                            },
                            "top": {
                                "type": "integer",
                                "description": "Anzahl Resultate (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "resolve_location",
                    "description": "Finde Koordinaten für eine Adresse, einen Ort, ein Gebäude oder Grundstück. VERWENDE DIES IMMER bei Fragen wie 'Wo liegt...', 'Auf welcher Höhe...', 'Zeige mir auf der Karte...'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Der gesuchte Ort. Beispiele: 'Bahnhof Luzern', 'Mürgi 1.1, 6025 Neudorf', 'Sursee', EGID oder EGRID"
                            },
                            "location_type": {
                                "type": "string",
                                "description": "Typ der Suche (optional): Adresse, Gemeinde, Ort, EGID, EGRID, Grundstück",
                                "enum": ["Adresse", "Gemeinde", "Ort", "EGID", "EGRID", "Grundstück"]
                            }
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_map_url",
                    "description": "Erstelle einen Link zur interaktiven Webkarte mit Marker. Verwende dies NACH resolve_location um dem Nutzer die Karte zu zeigen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "map_id": {
                                "type": "string",
                                "description": f"ID der Webkarte. Standard ist 'objekte/grundbuchplan'. Wenn du aber eine spezifischere Karte findest, nutze stattdessen die passende aus der Liste: {map_id}. Überprüfe das Array und wähle immer die thematisch treffendste Karte statt nur den Standard.",
                                "default": "objekte/grundbuchplan"
                            },
                            "coords": {
                                "type": "object",
                                "description": "Koordinaten im LV95 System (aus resolve_location)",
                                "properties": {
                                    "x": {"type": "number", "description": "X-Koordinate (cx vom LocationFinder)"},
                                    "y": {"type": "number", "description": "Y-Koordinate (cy vom LocationFinder)"}
                                },
                                "required": ["x", "y"]
                            }
                        },
                        "required": ["coords"]
                    }
                }
            }
        ]
    
    async def _execute_tool(self, tool_name: str, arguments: Dict) -> str:
        """Execute a tool and return results"""
        try:
            if tool_name == "search_metadata":
                query = arguments.get("query")
                top = arguments.get("top", 5)
                results = self.search_service.search(query, top=top)
                
                # Format for LLM with clear structure
                formatted = {
                    "found_datasets": len(results),
                    "results": []
                }
                
                for r in results:
                    formatted["results"].append({
                        'title': r['title'],
                        'metauid': r['metauid'],
                        'type': r['type'],
                        'description': r['content'][:200] + '...' if len(r['content']) > 200 else r['content'],
                        'keywords': r['keywords'],
                        'metadata_url': r['openly_url'],
                        'datashop_url': r['webapp_url'],
                        'relevance_score': round(r['score'], 3)
                    })
                
                return json.dumps(formatted, ensure_ascii=False, indent=2)
            
            elif tool_name == "resolve_location":
                location = arguments.get("location")
                location_type = arguments.get("location_type")
                
                try:
                    results = await self.location_service.resolve_location(location, location_type)
                    
                    if not results or len(results) == 0:
                        return json.dumps({
                            "status": "not_found",
                            "message": f"Keine Ergebnisse für '{location}' gefunden. Versuche es mit einer anderen Schreibweise oder füge mehr Details hinzu.",
                            "suggestions": [
                                "Versuche die vollständige Adresse (z.B. 'Bahnhofstrasse 1, Luzern')",
                                "Versuche nur den Ortsnamen (z.B. 'Luzern')",
                                "Prüfe die Schreibweise"
                            ]
                        }, ensure_ascii=False)
                    
                    # Format top results with clear coordinates
                    formatted = {
                        "status": "found",
                        "location_query": location,
                        "count": len(results),
                        "results": []
                    }
                    
                    for r in results[:3]:
                        formatted["results"].append({
                            "name": r.get("name"),
                            "type": r.get("type"),
                            "coordinates": {
                                "x": r.get("cx"),
                                "y": r.get("cy"),
                                "system": "LV95/EPSG:2056"
                            },
                            "extent": {
                                "xmin": r.get("xmin"),
                                "ymin": r.get("ymin"),
                                "xmax": r.get("xmax"),
                                "ymax": r.get("ymax")
                            },
                            "additional_info": r.get("fields", {})
                        })
                    
                    return json.dumps(formatted, ensure_ascii=False, indent=2)
                    
                except Exception as e:
                    
                    return json.dumps({
                        "status": "error",
                        "message": f"Fehler bei der Ortssuche: {str(e)}",
                        "location_query": location
                    }, ensure_ascii=False)
            
            elif tool_name == "generate_map_url":
                map_id = arguments.get("map_id", "/objekte/grundbuchplan/")
                coords_dict = arguments.get("coords")
                coords = (coords_dict['x'], coords_dict['y'])
                url = self.location_service.generate_map_url(map_id, coords)
                
                return json.dumps({
                    "map_url": url,
                    "coordinates": coords_dict,
                    "map_type": map_id,
                    "instructions": "Dieser Link öffnet die interaktive Karte mit einem Marker am gesuchten Standort."
                }, ensure_ascii=False, indent=2)
            
            return json.dumps({"error": "Unknown tool"}, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "tool": tool_name,
                "arguments": arguments
            }, ensure_ascii=False)
    
    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """Main chat function with function calling"""
        
        if conversation_history is None:
            conversation_history = []
        
        # Build messages
        messages = [
            {"role": "system", "content": self._get_system_prompt()}
        ] + conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        # Initial call to GPT-4o
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            tools=self._get_tools(),
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1500
        )
        
        assistant_message = response.choices[0].message
        
        # Handle function calls
        if assistant_message.tool_calls:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 Executing: {function_name}({function_args})")
                
                function_response = await self._execute_tool(function_name, function_args)
                
                # Add tool response
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": function_response
                })
            
            # Get final response from GPT-4o
            final_response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            assistant_message = final_response.choices[0].message
        
        return {
            "response": assistant_message.content,
            "conversation_history": messages[1:] + [{
                "role": "assistant",
                "content": assistant_message.content
            }]
        }


# Test
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    service = AzureOpenAIService()
    
    async def test_suite():
        print("=== Test 1: Suche nach Höhendaten ===")
        result1 = await service.chat("Welcher Datensatz zeigt mir Höhendaten?")
        print(result1["response"])
        
        print("\n=== Test 2: Suche nach Verkehrslärm-Daten ===")
        result2 = await service.chat("Gibt es Geodaten zum Verkehrslärm in Luzern?")
        print(result2["response"])
        
        print("\n=== Test 3: Standort auflösen (Adresse) ===")
        result3 = await service.chat("Finde die Koordinaten von Pilatusstrasse 1, Luzern")
        print(result3["response"])
        
        print("\n=== Test 4: Standort auflösen (Gemeinde) ===")
        result4 = await service.chat("Wo liegt die Gemeinde Kriens?")
        print(result4["response"])
        
        print("\n=== Test 5: Map-URL generieren ===")
        result5 = await service.chat(json.dumps({
            "tool": "generate_map_url",
            "coords": {"x": 683200, "y": 211300},
            "map_id": "oberflaechengewaesser"
        }))
        print(result5["response"])
        
        print("\n=== Test 6: Kombination Suche + Map ===")
        result6 = await service.chat("Zeige mir die Höhendaten als Marker auf der Karte")
        print(result6["response"])
    
    asyncio.run(test_suite())