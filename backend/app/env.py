from __future__ import annotations

import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)

BACKEND_ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE_PATH = BACKEND_ROOT_DIR / ".env"


def _strip_wrapping_quotes(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def load_backend_env() -> None:
    if not ENV_FILE_PATH.is_file():
        return

    try:
        for raw_line in ENV_FILE_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            normalized_key = key.strip()
            if not normalized_key:
                continue
            os.environ.setdefault(normalized_key, _strip_wrapping_quotes(value))
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load backend .env file %s: %s", ENV_FILE_PATH, exc)
