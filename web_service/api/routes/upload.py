"""
Upload API routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List

from web_service.services.session_manager import session_manager
from web_service.config import MAX_UPLOAD_SIZE, SUPPORTED_EXTENSIONS

router = APIRouter()


@router.post("/upload")
async def upload_file(session_id: str = Form(None), file: UploadFile = File(...)):
    """Upload a file to a session"""
    # Create session if not provided
    if not session_id:
        session_id = session_manager.create_session()

    # Check session exists, if not create with the given session_id
    session = session_manager.get_session(session_id)
    if not session:
        # Create session with the provided session_id
        session = session_manager.create_session_with_id(session_id)

    # Check file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {MAX_UPLOAD_SIZE // (1024*1024)}MB")

    # Check file extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    # Save file
    try:
        file_info = session_manager.add_file(session_id, file.filename, content)
        return {
            "session_id": session_id,
            "file": file_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/multiple")
async def upload_multiple_files(session_id: str = Form(None), files: List[UploadFile] = File(...)):
    """Upload multiple files to a session"""
    if not session_id:
        session_id = session_manager.create_session()

    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session_with_id(session_id)

    uploaded = []
    errors = []

    for file in files:
        try:
            content = await file.read()
            if len(content) > MAX_UPLOAD_SIZE:
                errors.append({"file": file.filename, "error": "File too large"})
                continue

            ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
            if f".{ext}" not in SUPPORTED_EXTENSIONS:
                errors.append({"file": file.filename, "error": "Unsupported file type"})
                continue

            file_info = session_manager.add_file(session_id, file.filename, content)
            uploaded.append(file_info)
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    return {
        "session_id": session_id,
        "uploaded": uploaded,
        "errors": errors
    }


@router.get("/session/{session_id}/files")
async def get_session_files(session_id: str):
    """Get all files in a session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "files": session_manager.get_files(session_id),
        "images": session_manager.get_images(session_id),
        "videos": session_manager.get_videos(session_id)
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_manager.delete_session(session_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Session not found")
