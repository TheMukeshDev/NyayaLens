"""Versioned prompt registry (Prompt-Strategy.md §16, AI-Evaluation.md §15).

Each production prompt has a stable version id (``{name}_prompt_{version}``,
e.g. ``qa_prompt_v1``). Builders are registered here so orchestrators can
resolve a task name to its latest prompt version in one call. Prompts and
schemas are stored in source control; document content is never stored in
prompt source files.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.ai.prompts.models import Prompt

_Builder = Callable[..., Prompt]


@dataclass(frozen=True)
class _Registration:
    version: str
    builder: _Builder


_REGISTRY: dict[str, _Registration] = {}


def prompt(name: str, version: str) -> Callable[[_Builder], _Builder]:
    """Register a prompt builder under ``{name}_prompt_{version}``."""

    def decorator(builder: _Builder) -> _Builder:
        _REGISTRY[f"{name}_prompt_{version}"] = _Registration(version=version, builder=builder)
        return builder

    return decorator


def get_prompt(name: str, *, version: str | None = None, **data: object) -> Prompt:
    """Build a prompt; without ``version`` the latest registered one is used."""
    version = version or latest_version(name)
    registration = _REGISTRY.get(f"{name}_prompt_{version}")
    if registration is None:
        raise KeyError(f"unknown prompt: {name}_prompt_{version}")
    prompt = registration.builder(**data)
    if prompt.version_id != f"{name}_prompt_{version}":
        raise ValueError("prompt builder returned a mismatched name/version")
    return prompt


def latest_version(name: str) -> str:
    candidates = [
        registration.version
        for key, registration in _REGISTRY.items()
        if key.startswith(f"{name}_prompt_")
    ]
    if not candidates:
        raise KeyError(f"no registered prompt for task: {name}")
    return max(candidates, key=_version_key)


def list_prompt_ids() -> list[str]:
    return sorted(_REGISTRY)


def _version_key(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version)
    return tuple(int(part) for part in parts) or (0,)