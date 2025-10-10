from pydantic import BaseModel

class FileUploadResponse(BaseModel):
    success: bool
    file_id: str
    filename: str
    message: str

class FileInfo(BaseModel):
    file_id: str
    filename: str
    upload_time: str
    file_size: int
    file_path: str