"""
Pydantic schemas for models
"""
from pydantic import BaseModel
from typing import List, Optional


class ModelInfo(BaseModel):
    id: str
    name: str
    display_name: str
    type: str
    task: str
    is_custom: bool = False


class ModelListResponse(BaseModel):
    models: List[ModelInfo]
    total: int


class FormatInfo(BaseModel):
    id: str
    name: str
    extension: str
    supports: List[str]


class FormatListResponse(BaseModel):
    formats: List[FormatInfo]
