from bwpatcher.version import __version__
from bwpatcher.detect import Detection, ModelDetectionError, detect_bytes, detect_model

__all__ = [
    "__version__",
    "Detection",
    "ModelDetectionError",
    "detect_bytes",
    "detect_model",
]
