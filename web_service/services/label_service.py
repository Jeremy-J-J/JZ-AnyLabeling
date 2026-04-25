"""
Label Service
Wraps the existing LabelConverter for format export
"""
import os
import sys
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web_service.config import RESULT_DIR, EXPORT_FORMATS
from web_service.schemas.model import FormatInfo, FormatListResponse


def convert_qpointf_to_serializable(obj):
    """Recursively convert QPointF and other PyQt types to JSON-serializable types"""
    from PyQt6.QtCore import QPointF, QPoint

    if isinstance(obj, QPointF):
        return {"x": obj.x(), "y": obj.y()}
    elif isinstance(obj, QPoint):
        return {"x": obj.x(), "y": obj.y()}
    elif isinstance(obj, dict):
        return {k: convert_qpointf_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_qpointf_to_serializable(item) for item in obj]
    else:
        return obj


# Format information
FORMAT_DETAILS = {
    "yolo": {
        "name": "YOLO",
        "extension": "txt",
        "supports": ["detection", "segmentation", "pose", "obb"]
    },
    "voc": {
        "name": "Pascal VOC",
        "extension": "xml",
        "supports": ["detection", "segmentation"]
    },
    "coco": {
        "name": "COCO JSON",
        "extension": "json",
        "supports": ["detection", "segmentation", "pose"]
    },
    "dota": {
        "name": "DOTA",
        "extension": "txt",
        "supports": ["detection", "obb"]
    },
    "mot": {
        "name": "MOT CSV",
        "extension": "csv",
        "supports": ["tracking"]
    },
    "mots": {
        "name": "MOTS PNG",
        "extension": "png",
        "supports": ["segmentation"]
    },
    "mask": {
        "name": "Mask PNG",
        "extension": "png",
        "supports": ["segmentation"]
    },
    "ppocr": {
        "name": "PaddleOCR JSON",
        "extension": "json",
        "supports": ["ocr"]
    }
}


class LabelService:
    """Service for label conversion and export"""

    def __init__(self):
        self.converter = None  # Lazy load
        self._init_converter()
        self.formats = self._load_formats()

    def _load_formats(self):
        """Load format definitions"""
        return FORMAT_DETAILS

    def _init_converter(self):
        """Initialize the label converter"""
        try:
            from anylabeling.views.labeling.label_converter import LabelConverter
            self.converter = LabelConverter()
        except Exception as e:
            print(f"Warning: Failed to initialize LabelConverter: {e}")

    def get_available_formats(self) -> FormatListResponse:
        """Get list of available export formats"""
        formats = []
        for fmt_id, details in FORMAT_DETAILS.items():
            format_info = FormatInfo(
                id=fmt_id,
                name=details["name"],
                extension=details["extension"],
                supports=details["supports"]
            )
            formats.append(format_info)

        return FormatListResponse(formats=formats, total=len(formats))

    def shapes_to_xlabel(self, shapes: List[Dict], image_path: str, image_data: bytes = None) -> Dict:
        """Convert shapes to XLabel JSON format"""
        return {
            "version": "1.0",
            "flags": {},
            "shapes": shapes,
            "imagePath": Path(image_path).name,
            "imageData": None,
            "imageHeight": 0,
            "imageWidth": 0
        }

    def export_to_format(
        self,
        shapes: List[Dict],
        image_path: str,
        output_format: str,
        output_dir: Optional[str] = None,
        classes: Optional[List[str]] = None
    ) -> str:
        """Export shapes to specified format"""
        if output_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported format: {output_format}")

        if output_dir is None:
            output_dir = str(RESULT_DIR / output_format)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # For now, save as JSON format directly to ensure files are saved
        # This preserves all shape data
        output_path = Path(output_dir) / f"{Path(image_path).stem}.json"

        # Convert QPointF objects to serializable types
        serializable_shapes = [convert_qpointf_to_serializable(shape) for shape in shapes]

        # Get image dimensions and copy image file
        image_height = 0
        image_width = 0
        image_filename = Path(image_path).name

        try:
            from PIL import Image
            with Image.open(image_path) as img:
                image_width, image_height = img.size
            # Copy image to output directory
            import shutil
            dest_image_path = Path(output_dir) / image_filename
            shutil.copy2(image_path, dest_image_path)
        except Exception as e:
            print(f"Warning: Could not process image file: {e}")

        label_data = {
            "version": "1.0",
            "flags": {},
            "shapes": serializable_shapes,
            "imagePath": image_filename,
            "imageHeight": image_height,
            "imageWidth": image_width,
            "output_format": output_format
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(label_data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(shapes)} shapes to {output_path}")

        return str(output_path)

    def create_result_package(
        self,
        job_id: str,
        annotations: List[Dict],
        output_format: str,
        save_path: Optional[str] = None
    ) -> str:
        """Create a result package with all annotations"""
        if save_path is None:
            save_path = RESULT_DIR / job_id
        else:
            save_path = Path(save_path)

        save_path.mkdir(parents=True, exist_ok=True)

        # Create result metadata
        metadata = {
            "job_id": job_id,
            "format": output_format,
            "created_at": datetime.now().isoformat(),
            "total_files": len(annotations)
        }

        with open(save_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Save individual annotations
        for i, ann in enumerate(annotations):
            ann_path = save_path / f"annotation_{i:04d}.json"
            with open(ann_path, "w") as f:
                json.dump(ann, f, indent=2)

        # Create zip of all annotations
        import zipfile
        zip_path = RESULT_DIR / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for ann in annotations:
                ann_file = save_path / f"{ann.get('imagePath', f'file_{ann.get('index', 0)}')}.json"
                if ann_file.exists():
                    zf.write(ann_file, ann_file.name)

        return str(zip_path)


# Global label service instance
label_service = LabelService()
