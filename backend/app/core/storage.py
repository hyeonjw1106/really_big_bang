from pathlib import Path
from app.core.config import settings


def storage_root() -> Path:
    root = Path(settings.DATA_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_subdir(name: str) -> Path:
    target = storage_root() / name
    target.mkdir(parents=True, exist_ok=True)
    return target
