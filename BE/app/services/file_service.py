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

    def get_file_content(self, file_id: str) -> str:
        """Retrieves the content of a specific file."""
        if file_id not in self.uploaded_files:
            raise HTTPException(status_code=404, detail="File not found.")
        
        file_info = self.uploaded_files[file_id]
        file_path = Path(file_info["file_path"])
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk.")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, "r", encoding="cp949") as f:
                return f.read()

    def list_files(self) -> List[FileInfo]:
        """Lists all uploaded files. Only returns files that actually exist on disk."""
        files = []
        files_to_remove = []
        
        for file_id, file_info in self.uploaded_files.items():
            file_path = Path(file_info.get("file_path", ""))
            
            # 실제 파일이 존재하는지 확인
            if file_path.exists() and file_path.is_file():
                files.append(
                    FileInfo(
                        file_id=file_id,
                        filename=file_info["filename"],
                        upload_time=file_info["upload_time"],
                        file_size=file_info["file_size"],
                        file_path=str(file_path)
                    )
                )
            else:
                # 파일이 없으면 목록에서 제거할 목록에 추가
                files_to_remove.append(file_id)
                logger.warning(f"File not found on disk, removing from list: {file_info.get('filename', file_id)}")
        
        # 존재하지 않는 파일들을 메모리에서 제거
        for file_id in files_to_remove:
            del self.uploaded_files[file_id]
        
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