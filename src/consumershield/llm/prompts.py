"""Find and load versioned prompts from the project's prompts directory."""

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def versions(directory: Path, task: str) -> list[str]:
    """Find prompt versions and sort them by version number."""
    pattern = re.compile(rf"^{re.escape(task)}_v(\d+)\.md$")
    found = []

    for path in directory.glob(f"{task}_v*.md"):
        match = pattern.match(path.name)
        if match:
            found.append((int(match.group(1)), path.stem))

    return [name for _, name in sorted(found)]


def latest(directory: Path, task: str) -> str:
    """Return the newest prompt version."""
    found = versions(directory, task)
    if not found:
        raise FileNotFoundError(f"No prompt versions found for {task}")
    return found[-1]


def read_prompt(directory: Path, version: str) -> str:
    """Read a specific prompt version."""
    path = directory / f"{version}.md"
    return path.read_text(encoding="utf-8").strip()
