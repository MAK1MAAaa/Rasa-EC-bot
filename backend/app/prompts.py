from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from .env import BACKEND_ROOT_DIR


PROMPT_DIR = BACKEND_ROOT_DIR / "prompts"
PROMPT_FILES = {
    "agent_final_answer": PROMPT_DIR / "agent_final_answer.md",
    "rasa_review": PROMPT_DIR / "rasa_review.md",
    "image_analysis": PROMPT_DIR / "image_analysis.md",
}


def get_prompt_path(name: str) -> Path:
    path = PROMPT_FILES.get((name or "").strip())
    if path is None:
        raise KeyError(f"Unknown prompt name: {name}")
    return path


@lru_cache(maxsize=None)
def load_prompt_text(name: str) -> str:
    path = get_prompt_path(name)
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise RuntimeError(f"Prompt file is empty: {path}")
    return text


def list_prompt_versions() -> list[dict[str, str]]:
    versions: list[dict[str, str]] = []
    for name, path in PROMPT_FILES.items():
        content = path.read_text(encoding="utf-8-sig")
        versions.append(
            {
                "name": name,
                "path": str(path.resolve()),
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )
    return versions
