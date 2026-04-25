"""
Formats API routes
"""
from fastapi import APIRouter

from web_service.services.label_service import label_service
from web_service.schemas.model import FormatListResponse

router = APIRouter()


@router.get("/formats", response_model=FormatListResponse)
async def get_formats():
    """Get list of all supported export formats"""
    return label_service.get_available_formats()
