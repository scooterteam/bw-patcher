from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _version_from_pyproject(path: Path) -> str:
    try:
        import tomllib

        with path.open("rb") as f:
            return tomllib.load(f)["tool"]["poetry"]["version"]
    except ImportError:
        pass

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version") and "=" in line:
            return line.split("=", 1)[1].strip().strip("\"'")
    raise ValueError("version not found in pyproject.toml")


if _pyproject.is_file():
    __version__ = _version_from_pyproject(_pyproject)
else:
    try:
        __version__ = version("bwpatcher")
    except PackageNotFoundError:
        __version__ = "0.0.0"
