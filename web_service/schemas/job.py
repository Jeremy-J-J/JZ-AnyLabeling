"""
Pydantic schemas for job processing
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LabelingMode(str, Enum):
    AUTO = "auto"  # Auto Recognition Mode: detect and annotate all classes
    CONFIGURED = "configured"  # Configured Class Mode: only annotate specified classes


class ProcessRequest(BaseModel):
    session_id: str
    model_id: str
    output_format: str
    options: Optional[Dict[str, Any]] = {}
    labeling_mode: LabelingMode = LabelingMode.AUTO
    specific_classes: Optional[List[str]] = None  # Only used if mode="configured"


class ProcessResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    current_file: Optional[str] = None
    total_files: Optional[int] = None
    error: Optional[str] = None
    result_path: Optional[str] = None
