"""
Preview API routes - for visualizing annotation results
"""
import os
import base64
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from web_service.config import RESULT_DIR, SESSION_DIR

router = APIRouter()


def get_label_file_path(image_path: str, label_dir: str = None) -> Optional[str]:
    """Get corresponding label file path for an image"""
    base_path = os.path.splitext(image_path)[0]

    # Try different label formats
    for ext in [".json"]:
        label_path = base_path + ext
        if os.path.exists(label_path):
            return label_path

    # Also check in label_dir if provided
    if label_dir:
        image_name = os.path.basename(image_path)
        label_path = os.path.join(label_dir, os.path.splitext(image_name)[0] + ".json")
        if os.path.exists(label_path):
            return label_path

    return None


def load_xlabel_json(label_path: str) -> dict:
    """Load XLabel format JSON file"""
    import json
    try:
        with open(label_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e), "shapes": []}


def shapes_to_geojson(shapes: list, image_width: int, image_height: int) -> dict:
    """Convert shapes to GeoJSON format for frontend rendering"""
    features = []
    for i, shape in enumerate(shapes):
        label = shape.get("label", "unknown")
        shape_type = shape.get("shape_type", "rectangle")
        points = shape.get("points", [])

        if not points:
            continue

        # Handle both [[x, y], ...] and [{"x": x, "y": y}, ...] formats
        def extract_coords(p):
            if isinstance(p, list) and len(p) >= 2:
                return [p[0], p[1]]
            elif isinstance(p, dict) and "x" in p and "y" in p:
                return [p["x"], p["y"]]
            return None

        extracted = [extract_coords(p) for p in points]
        extracted = [c for c in extracted if c is not None]

        if len(extracted) < 3:
            continue

        # Convert to GeoJSON coordinates (normalized 0-1)
        if shape_type in ["rectangle", "polygon", "quadrilateral"]:
            coords = [[c[0] / image_width, c[1] / image_height] for c in extracted]

            features.append({
                "type": "Feature",
                "properties": {
                    "id": i,
                    "label": label,
                    "score": shape.get("score"),
                    "shape_type": shape_type,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            })
        elif shape_type == "point" and len(extracted) >= 1:
            features.append({
                "type": "Feature",
                "properties": {
                    "id": i,
                    "label": label,
                    "score": shape.get("score"),
                    "shape_type": shape_type,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [extracted[0][0] / image_width, extracted[0][1] / image_height]
                }
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get("/preview/list")
async def list_preview_folder(folder_path: str = ""):
    """List all images in a folder with their annotation status"""
    if not folder_path:
        raise HTTPException(status_code=400, detail="folder_path is required")

    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    # Image extensions
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

    images = []
    for file in sorted(folder.iterdir()):
        if file.suffix.lower() in image_exts:
            # Look for label file
            label_path = get_label_file_path(str(file), str(folder))

            images.append({
                "name": file.name,
                "path": str(file),
                "has_annotation": label_path is not None,
                "label_path": label_path
            })

    return {
        "folder": str(folder),
        "images_count": len(images),
        "images": images
    }


@router.get("/preview/image")
async def get_preview_image(
    image_path: str = "",
    include_annotations: bool = True
):
    """Get image data with annotations for preview"""
    if not image_path:
        raise HTTPException(status_code=400, detail="image_path is required")

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    # Read image and convert to base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Get image extension
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".jpg":
        ext = ".jpeg"

    mime_type = f"image/{ext.lstrip('.')}"

    result = {
        "name": os.path.basename(image_path),
        "path": image_path,
        "data": f"data:{mime_type};base64,{image_data}"
    }

    if include_annotations:
        label_path = get_label_file_path(image_path)
        if label_path:
            label_data = load_xlabel_json(label_path)

            # Get image dimensions from label or from file
            width = label_data.get("imageWidth", 0)
            height = label_data.get("imageHeight", 0)

            # If dimensions not in label, try to get from image
            if width == 0 or height == 0:
                from PIL import Image as PILImage
                try:
                    with PILImage.open(image_path) as img:
                        width, height = img.size
                except:
                    pass

            result["annotations"] = shapes_to_geojson(
                label_data.get("shapes", []),
                width or 1,
                height or 1
            )
            result["shapes"] = label_data.get("shapes", [])
            result["width"] = width
            result["height"] = height

    return result


@router.get("/preview/folder")
async def get_folder_annotations(folder_path: str = ""):
    """Get all annotations in a folder as a summary"""
    if not folder_path:
        raise HTTPException(status_code=400, detail="folder_path is required")

    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

    all_annotations = []
    label_counts = {}

    for file in sorted(folder.iterdir()):
        if file.suffix.lower() not in image_exts:
            continue

        label_path = get_label_file_path(str(file), str(folder))
        if not label_path:
            continue

        label_data = load_xlabel_json(label_path)
        shapes = label_data.get("shapes", [])

        for shape in shapes:
            label = shape.get("label", "unknown")
            label_counts[label] = label_counts.get(label, 0) + 1

        all_annotations.append({
            "image": file.name,
            "shapes_count": len(shapes),
            "shapes": shapes
        })

    return {
        "folder": str(folder),
        "images_with_annotations": len(all_annotations),
        "total_shapes": sum(a["shapes_count"] for a in all_annotations),
        "label_distribution": label_counts,
        "annotations": all_annotations
    }