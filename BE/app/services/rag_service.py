import logging
import os
from pathlib import Path
from neo4j import GraphDatabase, Driver
from typing import Optional, Tuple, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

def find_existing_keyword() -> Optional[str]:
    """Find the keyword for existing embedding data."""
    import_dir = settings.IMPORT_DIRECTORY
    logger.info(f"🔍 Searching for embedding data in: {import_dir.absolute()}")

    if not import_dir.exists():
        logger.warning(f"❌ Import directory does not exist: {import_dir.absolute()}")
        return None

    # 1. Prioritize keyword from settings if it exists and has data
    if settings.KEYWORD:
        keyword_dir = import_dir / settings.KEYWORD
        if keyword_dir.exists():
            precompute_dir = keyword_dir / os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
            if precompute_dir.exists() and any(precompute_dir.glob("*_faiss.index")):
                logger.info(f"✅ Found embedding data for keyword from settings: {settings.KEYWORD}")
                return settings.KEYWORD

    # 2. Find the most recently modified keyword directory with FAISS files
    keyword_dirs = []
    for keyword_dir in import_dir.iterdir():
        if keyword_dir.is_dir():
            precompute_dir = keyword_dir / os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
            if precompute_dir.exists() and any(precompute_dir.glob("*_faiss.index")):
                mtime = keyword_dir.stat().st_mtime
                keyword_dirs.append((mtime, keyword_dir.name))

    if keyword_dirs:
        keyword_dirs.sort(key=lambda x: x[0], reverse=True)
        latest_keyword = keyword_dirs[0][1]
        logger.info(f"✅ Found latest embedding data by modification time: {latest_keyword}")
        return latest_keyword

    logger.warning("❌ Could not find any existing embedding data.")
    return None

def load_rag_system() -> Tuple[Optional[Dict[str, Any]], Optional[Driver]]:
    """Loads the RAG system and returns the system components and Neo4j driver."""
    try:
        from experiment.run_questions_v3_with_concept import load_enhanced_rag_system

        # This function from the original script is expected to use env vars for configuration
        enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver = load_enhanced_rag_system()

        rag_system = {
            "enhanced_lkg_retriever": enhanced_lkg_retriever,
            "hippo_retriever": hippo_retriever,
            "llm_generator": llm_generator
        }

        logger.info("✅ RAG system loaded successfully.")
        return rag_system, neo4j_driver

    except Exception as e:
        logger.error(f"❌ Failed to load RAG system: {e}", exc_info=True)
        return None, None

def check_and_load_existing_data() -> bool:
    """Checks for existing Neo4j data and loads the RAG system if found."""
    logger.info("🔍 Checking for existing Neo4j data...")
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]

            if node_count > 0:
                logger.info(f"✅ Found existing Neo4j data: {node_count} nodes.")
                existing_keyword = find_existing_keyword()
                if existing_keyword:
                    # Set the keyword in the environment for the RAG loading script to use
                    os.environ['KEYWORD'] = existing_keyword
                    settings.KEYWORD = existing_keyword
                    logger.info(f"🔑 Set KEYWORD for RAG system: {existing_keyword}")
                    return True
                else:
                    logger.info("ℹ️ Neo4j data exists, but no corresponding embedding data found.")
                    return False
            else:
                logger.info("ℹ️ No data found in Neo4j. Ready for a new pipeline run.")
                return False
    except Exception as e:
        logger.warning(f"⚠️ Failed to connect to Neo4j or check data: {e}")
        return False
    finally:
        if 'driver' in locals() and driver:
            driver.close()