from fastapi import APIRouter

from app.api.endpoints import chat, files, pipeline, status, neo4j
from riskAnalysis.risk_analysis_api import router as risk_analysis_router

api_router = APIRouter()

# Include chat-related endpoints
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Include file management endpoints
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# Include pipeline management endpoints
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])

# Include system status endpoints
api_router.include_router(status.router, prefix="/status", tags=["Status"])

# Include Neo4j endpoints
api_router.include_router(neo4j.router, tags=["Neo4j"])

# Include the existing risk analysis router
api_router.include_router(risk_analysis_router, prefix="/risk-analysis", tags=["Risk Analysis"])