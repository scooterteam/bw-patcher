from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"

if _pyproject.is_file():
    import tomllib

    with _pyproject.open("rb") as f:
        __version__ = tomllib.load(f)["tool"]["poetry"]["version"]
else:
    try:
        __version__ = version("bwpatcher")
    except PackageNotFoundError:
        __version__ = "0.0.0"
