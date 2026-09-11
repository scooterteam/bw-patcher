from bwpatcher.version import __version__

__all__ = [
    "__version__",
    "Detection",
    "ModelDetectionError",
    "detect_bytes",
    "detect_model",
]


def __getattr__(name):
    if name in ("Detection", "ModelDetectionError", "detect_bytes", "detect_model"):
        from bwpatcher import detect as _detect

        return getattr(_detect, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
