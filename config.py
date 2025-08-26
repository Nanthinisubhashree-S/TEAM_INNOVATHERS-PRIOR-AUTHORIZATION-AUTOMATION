DB_PATH = "prior_auth.db"

allowed_fractures = {
    "S72.0": ["S72.0", "S72.1", "S72.2", "S72.3"],
    "S82.5": ["S82.5", "S82.6", "S82.7", "S82.8"],
    "S52.5": ["S52.5", "S52.6", "S52.7", "S52.8"]
}

ONNX_MODEL_PATH = "yolov7-p6-bonefracture.onnx"