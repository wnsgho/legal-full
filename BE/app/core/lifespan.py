import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.dependencies import get_rag_system, close_rag_system
from app.services.file_service import restore_uploaded_files
from app.services.rag_service import check_and_load_existing_data

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    logger.info("🚀 Starting AutoSchemaKG Backend Server...")

    # Restore uploaded files state from the uploads directory
    restore_uploaded_files()

    # Check for existing data and load the RAG system if available
    data_loaded = check_and_load_existing_data()
    if not data_loaded:
        logger.info("ℹ️ No existing data found. Please upload a file and run the pipeline.")
    else:
        # Initialize the RAG system
        get_rag_system()

    yield

    # Shutdown
    logger.info("🛑 Shutting down AutoSchemaKG Backend Server...")
    close_rag_system()
    logger.info("✅ RAG system resources released.")