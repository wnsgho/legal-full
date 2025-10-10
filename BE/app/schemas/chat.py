from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    question: str
    max_tokens: int = 8192
    temperature: float = 0.5
    chat_mode: str = "rag"  # "rag" 또는 "openai"
    file_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    answer: str
    context_count: int
    processing_time: float