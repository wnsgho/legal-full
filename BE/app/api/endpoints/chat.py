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

@router.post("/openai-basic", response_model=ChatResponse)
async def openai_basic_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    OpenAI basic chat without RAG.
    """
    # Force chat_mode to openai for basic chat
    request.chat_mode = "openai"
    return await chat_service.process_chat_request(request)

@router.post("/openai-basic/{file_id}", response_model=ChatResponse)
async def openai_basic_chat_with_file(
    file_id: str,
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    OpenAI basic chat with a specific file context.
    """
    # Force chat_mode to openai and set file_id
    request.chat_mode = "openai"
    request.file_id = file_id
    return await chat_service.process_chat_request(request)

@router.delete("/history")
async def clear_chat_history():
    """
    Clear chat history.
    """
    # This is a placeholder implementation
    # In a real application, you would clear the chat history from storage
    return {"success": True, "message": "Chat history cleared"}

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