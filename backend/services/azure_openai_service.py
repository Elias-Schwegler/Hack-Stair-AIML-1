import os
import json
from typing import List, Dict, Optional
from openai import AzureOpenAI
import sys
sys.path.append('.')
from backend.services.azure_search_service import AzureSearchService
from backend.services.location_service import LocationService

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
4. Gib immer die Quellen (URLs) an

Verfügbare Tools:
- search_metadata: Suche nach Geodatensätzen in der Metadatenbank
- resolve_location: Finde Koordinaten für Adressen, Orte, EGID, EGRID
- generate_map_url: Erstelle Webkarten-Links mit Marker

Antworte:
- Auf Deutsch
- Präzise und hilfreich
- Mit konkreten Links zu Datensätzen
- Zitiere immer die Datenquellen (URLs)"""

    def _get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_metadata",
                    "description": "Suche nach Geodatensätzen und Collections in der Metadatenbank des Geoportals",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Suchbegriff für Geodaten (z.B. 'Höhendaten', 'Verkehrslärm', 'Gewässer')"
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
                    "description": "Finde Koordinaten für eine Adresse, einen Ort, EGID, EGRID oder Gebäudeversicherungsnummer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Adresse, Ortsname, EGID, EGRID oder Gebäudeversicherungsnummer"
                            },
                            "location_type": {
                                "type": "string",
                                "description": "Typ der Suche: Adresse, Gemeinde, Ort, EGID, EGRID, Grundstück",
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
                    "description": "Erstelle einen Link zur Webkarte mit Marker an bestimmten Koordinaten",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "map_id": {
                                "type": "string",
                                "description": "ID der Webkarte (z.B. 'grundbuchplan', 'oberflaechengewaesser')",
                                "default": "grundbuchplan"
                            },
                            "coords": {
                                "type": "object",
                                "description": "Koordinaten im LV95 System",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"}
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
                
                # Format for LLM
                formatted = []
                for r in results:
                    formatted.append({
                        'title': r['title'],
                        'metauid': r['metauid'],
                        'type': r['type'],
                        'keywords': r['keywords'],
                        'metadata_url': r['openly_url'],
                        'datashop_url': r['webapp_url'],
                        'relevance_score': round(r['score'], 3)
                    })
                
                return json.dumps(formatted, ensure_ascii=False, indent=2)
            
            elif tool_name == "resolve_location":
                location = arguments.get("location")
                location_type = arguments.get("location_type")
                results = await self.location_service.resolve_location(location, location_type)
                
                # Return top 3 results
                return json.dumps(results[:3], ensure_ascii=False, indent=2)
            
            elif tool_name == "generate_map_url":
                map_id = arguments.get("map_id", "grundbuchplan")
                coords_dict = arguments.get("coords")
                coords = (coords_dict['x'], coords_dict['y'])
                url = self.location_service.generate_map_url(map_id, coords)
                
                return json.dumps({"map_url": url}, ensure_ascii=False)
            
            return json.dumps({"error": "Unknown tool"}, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
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
    
    async def test():
        result = await service.chat("Welcher Datensatz zeigt mir Höhendaten?")
        print(result["response"])
    
    asyncio.run(test())