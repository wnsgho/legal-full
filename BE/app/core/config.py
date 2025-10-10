import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional

# Define the base directory for the BE part of the project
# This resolves to the 'BE' directory.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoSchemaKG Backend API"
    API_V1_STR: str = "/api/v1"

    # Base directory of the BE application
    BASE_DIR: Path = BASE_DIR

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_MODEL: str = "gpt-4.1-mini"

    # Neo4j
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str

    # Data directories
    UPLOAD_DIR: Path = BASE_DIR.parent / "uploads"
    DATA_DIRECTORY: Path = BASE_DIR / "example_data"
    IMPORT_DIRECTORY: Path = BASE_DIR / "import"
    OUTPUT_DIRECTORY: str = "output"
    LOG_DIRECTORY: str = "log"
    PRECOMPUTE_DIRECTORY: str = "precompute"

    # Pipeline
    KEYWORD: Optional[str] = None
    DEFAULT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        case_sensitive = True
        # Allow Pydantic to work with Path objects
        arbitrary_types_allowed = True
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()