from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.schemas.file import FileUploadResponse, FileInfo
from app.services.file_service import FileService, get_file_service

router = APIRouter()

@router.post("/upload/contract", response_model=FileUploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service)
):
    """
    Uploads a contract file.
    """
    try:
        result = await file_service.save_file(file)
        return FileUploadResponse(
            success=True,
            file_id=result["file_id"],
            filename=result["filename"],
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[FileInfo])
async def list_files(
    file_service: FileService = Depends(get_file_service)
):
    """
    Lists all uploaded files.
    """
    return file_service.list_files()


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Deletes a specific uploaded file.
    """
    try:
        result = file_service.delete_file(file_id)
        return {"success": True, "message": result["message"]}
    except HTTPException as e:
        # Re-raise HTTPException to ensure proper status codes are sent
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))