"""
Model Service
Wraps the existing ModelManager for web API access
"""
import os
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web_service.schemas.model import ModelInfo, ModelListResponse


# Task categories mapping
TASK_MAPPING = {
    "yolov5": "detection",
    "yolov6": "detection",
    "yolov7": "detection",
    "yolov8": "detection",
    "yolov9": "detection",
    "yolov10": "detection",
    "yolo11": "detection",
    "yolo26": "detection",
    "yoloe": "detection",
    "damoyolo": "detection",
    "rt-detr": "detection",
    "rtdetr": "detection",
    "dfine": "detection",
    "deimv2": "detection",
    "grounding": "grounding",
    "sam": "segmentation",
    "sam_hq": "segmentation",
    "sam2": "segmentation",
    "segment_anything": "segmentation",
    "yolo_seg": "segmentation",
    "yolo_segment": "segmentation",
    "pose": "pose",
    "rtmdet_pose": "pose",
    "yolo_pose": "pose",
    "obb": "obb",
    "yolo_obb": "obb",
    "ocr": "ocr",
    "ppocr": "ocr",
    "ram": "tagging",
    "depth": "depth",
    "depth_anything": "depth",
    "tracking": "tracking",
    "tracker": "tracking",
    "bot": "tracking",
    "bytetrack": "tracking",
    "classification": "classification",
    "cls": "classification",
}


def get_task_type(model_type: str) -> str:
    """Determine task type from model type/name"""
    model_type_lower = model_type.lower()
    for key, task in TASK_MAPPING.items():
        if key in model_type_lower:
            return task
    return "detection"  # Default


class ModelService:
    """Service for managing models"""

    def __init__(self):
        # Initialize anylabeling config before loading models
        self._init_anylabeling_config()

        self.model_configs = self._load_model_configs()
        self.loaded_models: Dict[str, Any] = {}

    def _init_anylabeling_config(self):
        """Initialize anylabeling config file"""
        import anylabeling.config as anylabeling_config
        config_path = Path(__file__).parent.parent.parent / "anylabeling" / "configs" / "xanylabeling_config.yaml"
        if config_path.exists():
            anylabeling_config.current_config_file = str(config_path)

    def _load_model_configs(self) -> List[Dict]:
        """Load model configurations from YAML"""
        configs = []
        config_dir = Path(__file__).parent.parent.parent / "anylabeling" / "configs" / "auto_labeling"

        if not config_dir.exists():
            return configs

        for config_file in config_dir.glob("*.yaml"):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if config:
                        config["config_file"] = str(config_file)
                        configs.append(config)
            except Exception:
                continue

        return configs

    def get_available_models(self) -> ModelListResponse:
        """Get list of all available models"""
        models = []
        for config in self.model_configs:
            model_type = config.get("type", "")
            task = get_task_type(model_type)

            model_info = ModelInfo(
                id=config.get("name", ""),
                name=config.get("name", ""),
                display_name=config.get("display_name", config.get("name", "")),
                type=model_type,
                task=task,
                is_custom=config.get("is_custom_model", False)
            )
            models.append(model_info)

        return ModelListResponse(models=models, total=len(models))

    def get_model_config(self, model_id: str) -> Optional[Dict]:
        """Get configuration for a specific model"""
        for config in self.model_configs:
            if config.get("name") == model_id:
                return config
        return None

    def load_model(self, model_id: str, options: Optional[Dict] = None) -> Any:
        """Load a model by ID"""
        # Check if already loaded
        if model_id in self.loaded_models:
            return self.loaded_models[model_id]

        config = self.get_model_config(model_id)
        if not config:
            raise ValueError(f"Model not found: {model_id}")

        # Merge options into config
        if options:
            config = {**config, **options}

        # Import the model class dynamically
        model_type = config.get("type", "")
        print(f"Loading model type: {model_type} (id: {model_id})")

        # Try to import the specific model module
        try:
            module_name = f"anylabeling.services.auto_labeling.{model_type}"
            print(f"Importing module: {module_name}")
            module = __import__(module_name, fromlist=["Model"])
            print(f"Module imported: {module}")

            # Find the Model class in the module
            model_class = None
            from anylabeling.services.auto_labeling.model import Model as BaseModel
            for attr_name in dir(module):
                if attr_name in ["Model", "YOLOBase", "SAMBase", "AutoLabelingResult", "ChineseClipONNX", "GenericWorker"]:
                    continue
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name[0].isupper():
                    # Check if this class is a subclass of Model
                    try:
                        if issubclass(attr, BaseModel):
                            model_class = attr
                            print(f"Found model class: {attr_name}")
                            break
                    except TypeError:
                        continue

            if model_class is None:
                raise ValueError(f"No model class found in {module_name}")

            # Create model instance
            def on_message(msg):
                print(f"Model message: {msg}")

            print(f"Creating model instance with config: {config.get('name')}")
            model = model_class(config, on_message)
            print(f"Model instance created: {model}")
            print(f"Model classes: {model.classes}")
            self.loaded_models[model_id] = model
            return model

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Failed to load model {model_id}: {str(e)}")

    def unload_model(self, model_id: str) -> bool:
        """Unload a model"""
        if model_id in self.loaded_models:
            model = self.loaded_models.pop(model_id)
            try:
                model.unload()
            except Exception:
                pass
            return True
        return False

    def predict(self, model_id: str, image_path: str, options: Optional[Dict] = None) -> Any:
        """Run prediction on an image"""
        model = self.load_model(model_id, options)

        # Handle confidence threshold
        conf_threshold = options.get("conf_threshold") if options else None
        if conf_threshold is not None:
            model.set_auto_labeling_conf(conf_threshold)
            print(f"Set confidence threshold to: {conf_threshold}")

        # For segmentation models like SAM-HQ, set default marks (full image prompt)
        if hasattr(model, 'set_auto_labeling_marks'):
            # Default: use a rectangle covering the whole image as prompt
            from PIL import Image
            with Image.open(image_path) as img:
                width, height = img.size
            # Use center point with label "all" to detect all objects
            default_marks = [{"type": "rectangle", "data": [0, 0, width, height]}]
            model.set_auto_labeling_marks(default_marks)
            print(f"Set auto labeling marks for segmentation model")

        # Handle labeling mode
        labeling_mode = options.get("labeling_mode", "auto") if options else "auto"
        specific_classes = options.get("specific_classes") if options else None

        if labeling_mode == "configured" and specific_classes:
            # Configured Class Mode: filter to only specified classes
            print(f"Configured mode: only annotating classes {specific_classes}")
            model.set_auto_labeling_filter_classes(specific_classes)
            print(f"Filter classes indices: {model.filter_classes}")
        else:
            # Auto Recognition Mode: no filtering (annotate all detected classes)
            print(f"Auto mode: annotating all detected classes")
            model.set_auto_labeling_filter_classes(None)
            print(f"Filter classes indices: {model.filter_classes}")

        # Load image
        from PIL import Image
        import numpy as np

        img = Image.open(image_path)
        img_array = np.array(img)

        # Run inference
        result = model.predict_shapes(img_array, image_path=image_path)
        return result


# Global model service instance
model_service = ModelService()
