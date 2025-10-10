from pydantic import BaseModel
from typing import Optional, Dict, Any

class PipelineRequest(BaseModel):
    start_step: int = 0
    keyword: Optional[str] = None

class PipelineResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class PipelineStatusResponse(BaseModel):
    success: bool
    status: str
    progress: int
    message: str
    data: Optional[Dict[str, Any]] = None