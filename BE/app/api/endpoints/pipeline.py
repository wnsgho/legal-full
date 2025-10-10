from fastapi import APIRouter, Depends, BackgroundTasks, Form
from app.schemas.pipeline import PipelineResponse, PipelineStatusResponse
from app.services.pipeline_service import PipelineService, get_pipeline_service

router = APIRouter()

@router.post("/run-with-file", response_model=PipelineResponse)
async def run_pipeline_with_file(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    start_step: int = Form(1),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Runs the ATLAS pipeline with a previously uploaded file.
    """
    result = pipeline_service.run_pipeline_with_file(
        file_id=file_id,
        start_step=start_step,
        background_tasks=background_tasks,
    )
    return PipelineResponse(
        success=True,
        message="Pipeline is running in the background.",
        data=result
    )

@router.get("/status/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    pipeline_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Retrieves the status of a running pipeline.
    """
    status_info = pipeline_service.get_pipeline_status(pipeline_id)
    return PipelineStatusResponse(
        success=True,
        status=status_info.get("status", "unknown"),
        progress=status_info.get("progress", 0),
        message=status_info.get("message", ""),
        data=status_info
    )