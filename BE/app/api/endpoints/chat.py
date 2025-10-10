from fastapi import APIRouter, Depends
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService, get_chat_service

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Handles chat requests, routing to either RAG or basic OpenAI based on the request.
    """
    return await chat_service.process_chat_request(request)

@router.post("/analyze-risks", response_model=ChatResponse)
async def analyze_risks(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Endpoint for analyzing contract risks.
    This is now routed through the chat service with a specific system prompt.
    """
    # The logic for risk analysis is handled by the RAG chat with a specialized prompt.
    # We can adjust the request or system prompt if needed here.
    return await chat_service.process_chat_request(request)