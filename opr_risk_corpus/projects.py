from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_projects(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required to read projects.yaml")
    data = yaml.safe_load(text) or {}
    projects = data.get("projects") or []
    if not isinstance(projects, list):
        raise ValueError("projects.yaml: 'projects' must be a list")
    out: list[dict[str, Any]] = []
    for item in projects:
        if not isinstance(item, dict) or "repo" not in item:
            continue
        repo = str(item["repo"])
        name = str(item.get("name") or repo.split("/")[-1])
        git = str(item.get("git") or f"https://github.com/{repo}.git")
        out.append({"repo": repo, "name": name, "git": git})
    return out
