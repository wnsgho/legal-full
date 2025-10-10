import logging
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import BackgroundTasks, HTTPException

from app.core.config import settings
from app.schemas.pipeline import PipelineResponse, PipelineStatusResponse
from app.services.file_service import FileService

logger = logging.getLogger(__name__)

class PipelineService:
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        self.pipeline_status: Dict[str, Dict[str, Any]] = {}

    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Retrieves the status of a specific pipeline."""
        if pipeline_id not in self.pipeline_status:
            raise HTTPException(status_code=404, detail="Pipeline not found.")
        return self.pipeline_status[pipeline_id]

    def run_pipeline_with_file(
        self,
        file_id: str,
        start_step: int,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """Prepares a file and runs the pipeline in the background."""
        file_info = self.file_service.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found.")

        file_path = Path(file_info["file_path"])
        keyword = f"contract_{file_id}"

        # Prepare file for the pipeline
        self._prepare_pipeline_file(file_path, keyword)

        pipeline_id = str(uuid.uuid4())

        # Determine the actual start step for the pipeline script
        actual_start_step = 0 if start_step == 1 else start_step

        background_tasks.add_task(
            self._execute_pipeline_process, actual_start_step, keyword, pipeline_id
        )

        return {
            "pipeline_id": pipeline_id,
            "keyword": keyword,
            "file_info": file_info,
        }

    def _prepare_pipeline_file(self, file_path: Path, keyword: str):
        """Copies and prepares the file for the pipeline based on its extension."""
        example_data_dir = settings.DATA_DIRECTORY
        example_data_dir.mkdir(exist_ok=True)
        file_ext = file_path.suffix.lower()

        if file_ext == '.json':
            target_path = example_data_dir / f"{keyword}.json"
            shutil.copy2(file_path, target_path)
        elif file_ext in ['.txt', '.md']:
            md_data_dir = example_data_dir / "md_data"
            md_data_dir.mkdir(exist_ok=True)
            target_path = md_data_dir / f"{keyword}{file_ext}"
            shutil.copy2(file_path, target_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

    def _execute_pipeline_process(
        self, start_step: int, keyword: str, pipeline_id: str
    ):
        """Executes the main_pipeline.py script as a subprocess."""
        logger.info(f"🚀 Starting pipeline process for keyword: {keyword}, start_step: {start_step}")
        self.pipeline_status[pipeline_id] = {
            "status": "running",
            "progress": 0,
            "message": "🚀 Pipeline execution started.",
            "start_time": datetime.now().isoformat(),
        }

        try:
            be_dir = settings.BASE_DIR
            cmd = [sys.executable, str(be_dir / "main_pipeline.py"), str(start_step), keyword]

            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['KEYWORD'] = keyword

            self.pipeline_status[pipeline_id]["progress"] = 25
            self.pipeline_status[pipeline_id]["message"] = "📋 Starting pipeline process..."

            result = subprocess.run(
                cmd,
                cwd=be_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                env=env,
                timeout=3600,  # 1-hour timeout
            )

            if result.returncode == 0:
                logger.info(f"✅ Pipeline completed successfully for {keyword}.")
                from app.services.rag_service import check_and_load_existing_data
                check_and_load_existing_data() # Reload RAG system with new data

                self.pipeline_status[pipeline_id].update({
                    "status": "completed",
                    "progress": 100,
                    "message": "✅ Pipeline finished successfully. RAG system is ready.",
                    "end_time": datetime.now().isoformat(),
                })
            else:
                logger.error(f"❌ Pipeline failed for {keyword}. Stderr: {result.stderr}")
                self.pipeline_status[pipeline_id].update({
                    "status": "failed",
                    "message": f"❌ Pipeline failed. Details: {result.stderr[:500]}",
                    "end_time": datetime.now().isoformat(),
                })

        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Pipeline timed out for keyword: {keyword}")
            self.pipeline_status[pipeline_id].update({
                "status": "failed",
                "message": "⏰ Pipeline execution timed out.",
                "end_time": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.error(f"❌ Pipeline execution error for {keyword}: {e}", exc_info=True)
            self.pipeline_status[pipeline_id].update({
                "status": "failed",
                "message": f"❌ An unexpected error occurred: {e}",
                "end_time": datetime.now().isoformat(),
            })

from .file_service import get_file_service

pipeline_service = PipelineService(file_service=get_file_service())

def get_pipeline_service() -> PipelineService:
    return pipeline_service