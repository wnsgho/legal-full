import logging
import os
from typing import Optional, Dict

from neo4j import GraphDatabase, Driver

from app.core.config import settings

logger = logging.getLogger(__name__)

# Application-level state
class AppState:
    def __init__(self):
        self.rag_system: Optional[Dict] = None
        self.neo4j_driver: Optional[Driver] = None

    def get_rag_system(self) -> Optional[Dict]:
        if self.rag_system is None:
            from app.services.rag_service import load_rag_system
            self.rag_system, self.neo4j_driver = load_rag_system()
        return self.rag_system

    def get_neo4j_driver(self) -> Optional[Driver]:
        if self.neo4j_driver is None:
            # Attempt to get it from the RAG system initialization first
            self.get_rag_system()

        # If still None, create a new one
        if self.neo4j_driver is None:
            try:
                self.neo4j_driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                logger.info("✅ Created a new Neo4j driver instance.")
            except Exception as e:
                logger.error(f"❌ Failed to create Neo4j driver: {e}")
                return None
        return self.neo4j_driver

    def close_resources(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
            self.neo4j_driver = None
            logger.info("✅ Neo4j driver closed.")
        self.rag_system = None
        logger.info("✅ RAG system resources released.")

app_state = AppState()

def get_rag_system() -> Optional[Dict]:
    return app_state.get_rag_system()

def get_neo4j_driver() -> Optional[Driver]:
    return app_state.get_neo4j_driver()

def close_rag_system():
    app_state.close_resources()