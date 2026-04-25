"""
Web Service Configuration
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Upload settings
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Session settings
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

# Result settings
RESULT_DIR = BASE_DIR / "results"
RESULT_DIR.mkdir(exist_ok=True)

# Max upload size (100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024

# Supported image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# Supported video formats
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".m4v", ".mpeg", ".mpg", ".ts", ".wmv", ".asf"}

# Supported export formats
EXPORT_FORMATS = ["yolo", "voc", "coco", "dota", "mot", "mots", "mask", "ppocr"]

# Get all supported file extensions
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
