import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import UploadFile, HTTPException

from app.core.config import settings
from app.schemas.file import FileInfo

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(exist_ok=True)
        self.uploaded_files: Dict[str, Dict] = {}

    def restore_uploaded_files(self):
        """Restore the state of uploaded files from the directory."""
        if not self.upload_dir.exists():
            return

        files_with_time = []
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file():
                files_with_time.append((file_path, file_path.stat().st_mtime))

        files_with_time.sort(key=lambda x: x[1], reverse=True)

        if files_with_time:
            file_path, _ = files_with_time[0]
            filename = file_path.name
            if '_' in filename:
                file_id = filename.split('_')[0]
                original_filename = '_'.join(filename.split('_')[1:])

                self.uploaded_files[file_id] = {
                    "filename": original_filename,
                    "file_path": str(file_path),
                    "upload_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "file_size": file_path.stat().st_size
                }
                logger.info(f"✅ Restored latest uploaded file: {original_filename} (ID: {file_id})")

    async def save_file(self, file: UploadFile) -> Dict:
        """Saves an uploaded file."""
        file_id = str(uuid.uuid4())
        file_path = self.upload_dir / f"{file_id}_{file.filename}"

        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            file_info = {
                "filename": file.filename,
                "file_path": str(file_path),
                "upload_time": datetime.now().isoformat(),
                "file_size": len(content)
            }
            self.uploaded_files[file_id] = file_info
            logger.info(f"File uploaded: {file.filename} (ID: {file_id})")

            return {"file_id": file_id, "filename": file.filename, "message": "File uploaded successfully."}
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Retrieves information about a specific file."""
        return self.uploaded_files.get(file_id)

    def list_files(self) -> List[FileInfo]:
        """Lists all uploaded files."""
        files = []
        for file_id, file_info in self.uploaded_files.items():
            files.append(
                FileInfo(
                    file_id=file_id,
                    filename=file_info["filename"],
                    upload_time=file_info["upload_time"],
                    file_size=file_info["file_size"],
                    file_path=file_info.get("file_path", "")
                )
            )
        return files

    def delete_file(self, file_id: str) -> Dict:
        """Deletes a specific file."""
        if file_id not in self.uploaded_files:
            raise HTTPException(status_code=404, detail="File not found.")

        file_info = self.uploaded_files[file_id]
        file_path = Path(file_info["file_path"])

        if file_path.exists():
            file_path.unlink()

        del self.uploaded_files[file_id]
        logger.info(f"File deleted: {file_info['filename']}")

        return {"message": "File deleted successfully."}

# Create a singleton instance of the FileService
file_service = FileService(upload_dir=settings.UPLOAD_DIR)

def get_file_service() -> FileService:
    return file_service

def restore_uploaded_files():
    file_service.restore_uploaded_files()