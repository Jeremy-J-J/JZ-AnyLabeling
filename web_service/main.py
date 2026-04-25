"""
X-AnyLabeling Web Service
FastAPI application entry point
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_service.config import UPLOAD_DIR, SESSION_DIR, RESULT_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="JZ-AnyLabeling",
    description="Auto Labeling Service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheStaticFiles(StaticFiles):
    """Static files with no cache headers for development hot reload"""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# Mount static files for UI with no-cache headers
ui_path = Path(__file__).parent / "ui"
if ui_path.exists():
    app.mount("/static", NoCacheStaticFiles(directory=str(ui_path)), name="static")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "JZ-AnyLabeling"}


# Diagnostic endpoint
@app.get("/api/diag")
async def diagnostic():
    """Test if core components work"""
    from web_service.services.model_service import model_service
    from web_service.services.label_service import label_service

    results = {
        "models_count": len(model_service.model_configs),
        "formats_count": len(label_service.formats),
    }

    # Try to load a model config
    yolo_configs = [c for c in model_service.model_configs if c.get("type") == "yolov8"]
    results["yolov8_configs"] = len(yolo_configs)
    if yolo_configs:
        results["sample_model"] = yolo_configs[0].get("name")

    return results


# Redirect root to UI
@app.get("/")
async def root():
    ui_file = Path(__file__).parent / "ui" / "index.html"
    if ui_file.exists():
        return RedirectResponse(url="/static/index.html")
    return {"message": "X-AnyLabeling Web Service", "docs": "/docs"}


# Import and include API routes
from web_service.api.routes import upload, process, models, formats

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(models.router, prefix="/api", tags=["models"])
app.include_router(formats.router, prefix="/api", tags=["formats"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
