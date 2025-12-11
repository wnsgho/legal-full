from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime

from app.schemas.health import HealthResponse
from app.core.config import settings
from app.core.dependencies import get_rag_system, get_neo4j_driver
from neo4j import Driver

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to confirm the server is running.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0"
    )

@router.get("/", response_model=Dict[str, Any])
async def get_system_status(
    rag_system: Dict = Depends(get_rag_system),
    neo4j_driver: Driver = Depends(get_neo4j_driver)
):
    """
    Provides the overall status of the application components.
    """
    neo4j_connected = False
    if neo4j_driver:
        try:
            with neo4j_driver.session() as session:
                session.run("RETURN 1")
            neo4j_connected = True
        except Exception:
            neo4j_connected = False

    status = {
        "rag_system_loaded": rag_system is not None,
        "neo4j_connected": neo4j_connected,
        "timestamp": datetime.now().isoformat(),
        "project_name": settings.PROJECT_NAME,
        "neo4j_database": settings.NEO4J_DATABASE,
    }

    return {"success": True, "status": status}