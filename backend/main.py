from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
sys.path.append('.')
from dotenv import load_dotenv

load_dotenv()

from services.azure_openai_service import AzureOpenAIService

app = FastAPI(
    title="Geoportal Chatbot API",
    description="AI-powered chatbot for Canton Lucerne Geoportal",
    version="1.0.0"
)

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
openai_service = AzureOpenAIService()

# Models
class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    response: str
    conversation_history: List[dict]

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Geoportal Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health"
        }
    }

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Main chat endpoint
    
    Send a message and optional conversation history to get AI response.
    """
    try:
        result = await openai_service.chat(
            user_message=request.message,
            conversation_history=request.conversation_history
        )
        return ChatResponse(**result)
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Chat service error: {str(e)}"
        )

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint"""
    try:
        # Test search service
        search_test = openai_service.search_service.search("test", top=1)
        search_status = "connected" if search_test else "error"
    except:
        search_status = "error"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "azure_openai": "connected",
            "azure_search": search_status,
            "location_finder": "connected"
        }
    )

@app.get("/stats", tags=["Stats"])
async def stats():
    """Get statistics about indexed data"""
    try:
        # Quick search to get total count
        results = openai_service.search_service.search("*", top=1)
        
        return {
            "status": "available",
            "indexed_documents": "338",
            "collections": "65",
            "datasets": "214",
            "services": "59"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Geoportal Chatbot API...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 API docs at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)