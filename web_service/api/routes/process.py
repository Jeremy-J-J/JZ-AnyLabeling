"""
Process API routes
"""
import os
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException

from web_service.services.session_manager import session_manager
from web_service.services.model_service import model_service
from web_service.services.label_service import label_service
from web_service.schemas.job import (
    ProcessRequest,
    ProcessResponse,
    JobStatus,
    JobStatusResponse
)
from web_service.config import RESULT_DIR

router = APIRouter()

# In-memory job storage
jobs = {}


@router.post("/process")
def start_processing(request: ProcessRequest):
    """Start a labeling processing job"""
    job_id = str(uuid.uuid4())

    # Validate session
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate model
    model_config = model_service.get_model_config(request.model_id)
    if not model_config:
        raise HTTPException(status_code=404, detail="Model not found")

    # Initialize job
    jobs[job_id] = {
        "id": job_id,
        "status": JobStatus.PENDING,
        "progress": 0,
        "session_id": request.session_id,
        "model_id": request.model_id,
        "output_format": request.output_format,
        "options": request.options or {},
        "labeling_mode": request.labeling_mode.value if request.labeling_mode else "auto",
        "specific_classes": request.specific_classes,
        "current_file": None,
        "total_files": 0,
        "error": None,
        "result_path": None
    }

    # Run processing in background thread so we can return immediately
    thread = threading.Thread(target=process_job, args=(job_id,))
    thread.daemon = True
    thread.start()

    return {
        "job_id": job_id,
        "status": jobs[job_id]["status"],
        "error": jobs[job_id].get("error"),
        "progress": jobs[job_id]["progress"],
        "result_path": jobs[job_id].get("result_path")
    }


def process_job(job_id: str):
    """Process a labeling job"""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        job["status"] = JobStatus.PROCESSING
        session = session_manager.get_session(job["session_id"])
        model_id = job["model_id"]
        output_format = job["output_format"]
        options = job.get("options", {})

        # Add labeling mode options
        labeling_mode = job.get("labeling_mode", "auto")
        specific_classes = job.get("specific_classes")
        options["labeling_mode"] = labeling_mode
        if specific_classes:
            options["specific_classes"] = specific_classes

        # Get frame interval for video processing
        frame_interval = options.get("frame_interval", 30)

        # Get custom save path if provided
        custom_save_path = options.get("save_path")
        if custom_save_path:
            result_dir = Path(custom_save_path)
        else:
            result_dir = RESULT_DIR / job_id
        result_dir.mkdir(parents=True, exist_ok=True)

        # Get images to process
        images = session_manager.get_images(job["session_id"])
        videos = session_manager.get_videos(job["session_id"])

        # Extract frames from videos
        all_files = list(images)
        for video in videos:
            frames = session_manager.extract_video_frames(job["session_id"], video["path"], frame_interval)
            for frame_path in frames:
                all_files.append({
                    "name": Path(frame_path).name,
                    "path": frame_path,
                    "type": "image"
                })

        job["total_files"] = len(all_files)

        # Process each file
        processed_count = 0
        for i, file_info in enumerate(all_files):
            job["current_file"] = file_info["name"]
            job["progress"] = int((i / len(all_files)) * 100)

            try:
                # Run prediction
                print(f"Processing {file_info['name']} with model {model_id}")
                prediction = model_service.predict(model_id, file_info["path"], job["options"])

                # Convert prediction to shapes
                shapes = []
                if prediction and hasattr(prediction, 'shapes'):
                    print(f"Raw prediction shapes count: {len(prediction.shapes)}")
                    for shape in prediction.shapes:
                        shape_dict = {
                            "label": getattr(shape, 'label', ''),
                            "score": getattr(shape, 'score', None),
                            "points": getattr(shape, 'points', []),
                            "shape_type": getattr(shape, 'shape_type', ''),
                            "group_id": getattr(shape, 'group_id', None),
                            "description": getattr(shape, 'description', ''),
                            "attributes": getattr(shape, 'attributes', {}),
                            "flags": getattr(shape, 'flags', {})
                        }
                        print(f"  Shape: label={shape_dict['label']}, score={shape_dict['score']}, points={len(shape_dict['points'])}")
                        shapes.append(shape_dict)

                print(f"Found {len(shapes)} shapes in {file_info['name']}")

                # Export to format
                print(f"Calling export_to_format with shapes={len(shapes)}, image_path={image_path}, output_format={output_format}")
                export_result = label_service.export_to_format(
                    shapes=shapes,
                    image_path=file_info["path"],
                    output_format=output_format,
                    output_dir=str(result_dir)
                )
                print(f"Export result: {export_result}")

                processed_count += 1

            except Exception as e:
                # Log error but continue processing
                print(f"Error processing {file_info['name']}: {e}")
                import traceback
                traceback.print_exc()
                # Store error in job results
                job["last_error"] = str(e)

        # Job completed
        job["progress"] = 100
        job["status"] = JobStatus.COMPLETED
        job["result_path"] = str(result_dir)
        job["processed_count"] = processed_count

    except Exception as e:
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a processing job"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        current_file=job["current_file"],
        total_files=job["total_files"],
        error=job["error"]
    )


@router.get("/result/{job_id}")
async def get_job_result(job_id: str):
    """Get result info of a completed job"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "result_path": job.get("result_path"),
        "processed_count": job.get("processed_count", 0)
    }
