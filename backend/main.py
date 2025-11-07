from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

from backend.services.azure_openai_service import AzureOpenAIService

app = FastAPI(
    title="Geoportal Chatbot API",
    description="AI-powered chatbot for Canton Lucerne Geoportal",
    version="1.0.0"
)

# CORS
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

@app.get("/")
async def root():
    return {
        "message": "Geoportal Chatbot API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        result = await openai_service.chat(
            user_message=request.message,
            conversation_history=request.conversation_history
        )
        return ChatResponse(**result)
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "azure_openai": "connected",
        "azure_search": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)