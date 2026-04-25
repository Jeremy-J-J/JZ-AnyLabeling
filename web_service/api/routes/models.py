"""
Models API routes
"""
from fastapi import APIRouter

from web_service.services.model_service import model_service
from web_service.schemas.model import ModelListResponse

router = APIRouter()


@router.get("/models", response_model=ModelListResponse)
async def get_models():
    """Get list of all available models"""
    return model_service.get_available_models()


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    """Get details of a specific model"""
    config = model_service.get_model_config(model_id)
    if not config:
        return {"error": "Model not found"}, 404
    return {"model_id": model_id, "config": config}
