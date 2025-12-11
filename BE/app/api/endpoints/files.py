from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Form
from app.schemas.file import FileUploadResponse, FileInfo
from app.services.file_service import FileService, get_file_service
from app.services.pipeline_service import PipelineService, get_pipeline_service

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


@router.get("/")
async def list_files(
    file_service: FileService = Depends(get_file_service)
):
    """
    Lists all uploaded files.
    """
    files = file_service.list_files()
    return {
        "success": True,
        "data": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "upload_time": f.upload_time,
                "file_size": f.file_size,
                "file_path": f.file_path
            }
            for f in files
        ]
    }


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Gets the content of a specific uploaded file.
    """
    try:
        content = file_service.get_file_content(file_id)
        return {"success": True, "data": {"content": content}}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


@router.post("/upload-and-run")
async def upload_and_run_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    start_step: int = Form(0),
    neo4j_database: str = Form(None),  # 사용할 Neo4j 데이터베이스 (None이면 환경변수 사용)
    file_service: FileService = Depends(get_file_service),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Uploads a file and immediately runs the ATLAS pipeline.
    
    Args:
        file: 업로드할 파일
        start_step: 파이프라인 시작 단계 (기본값: 0)
        neo4j_database: 사용할 Neo4j 데이터베이스 이름 (None이면 환경변수 NEO4J_DATABASE 사용)
    """
    try:
        # 1. 파일 업로드
        file_result = await file_service.save_file(file)
        
        # 2. 파이프라인 실행
        pipeline_result = pipeline_service.run_pipeline_with_file(
            file_id=file_result["file_id"],
            start_step=start_step,
            background_tasks=background_tasks,
            neo4j_database=neo4j_database,
        )
        
        return {
            "success": True,
            "message": "File uploaded and pipeline started successfully.",
            "data": {
                "pipeline_id": pipeline_result["pipeline_id"],
                "keyword": pipeline_result.get("keyword", ""),
                "neo4j_database": pipeline_result.get("neo4j_database", ""),
                "file_info": {
                    "file_id": file_result["file_id"],
                    "filename": file_result["filename"],
                    "file_size": file_result.get("file_size", 0),
                    "upload_time": file_result.get("upload_time", "")
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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