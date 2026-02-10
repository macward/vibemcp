"""File walker for discovering files in VIBE_ROOT."""

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a discovered file."""

    path: Path  # Absolute path
    relative_path: str  # Relative to VIBE_ROOT
    project_name: str
    folder: str  # tasks, plans, sessions, etc. or "" for root files
    filename: str
    mtime: float
    content_hash: str


def compute_hash(content: bytes) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content).hexdigest()


def walk_vibe_root(vibe_root: Path) -> Iterator[FileInfo]:
    """
    Walk the VIBE_ROOT directory and yield FileInfo for each .md file.

    Structure expected:
    <VIBE_ROOT>/
    ├── project1/
    │   ├── status.md
    │   ├── tasks/
    │   │   ├── 001-foo.md
    │   │   └── 002-bar.md
    │   ├── plans/
    │   │   └── execution-plan.md
    │   └── ...
    └── project2/
        └── ...
    """
    if not vibe_root.exists():
        return

    # Iterate over project directories
    for project_dir in sorted(vibe_root.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_dir.name.startswith("."):
            continue  # Skip hidden directories

        project_name = project_dir.name

        # Walk all files in the project
        for file_path in project_dir.rglob("*.md"):
            if not file_path.is_file():
                continue

            # Skip hidden files and directories
            relative_parts = file_path.relative_to(project_dir).parts
            if any(part.startswith(".") for part in relative_parts):
                continue

            # Determine folder (first directory level, or "" for root files)
            if len(relative_parts) > 1:
                folder = relative_parts[0]
            else:
                folder = ""  # Root-level file like status.md

            # Compute relative path from VIBE_ROOT
            relative_path = str(file_path.relative_to(vibe_root))

            # Get file stats
            stat = file_path.stat()
            mtime = stat.st_mtime

            # Read content and compute hash
            content = file_path.read_bytes()
            content_hash = compute_hash(content)

            yield FileInfo(
                path=file_path,
                relative_path=relative_path,
                project_name=project_name,
                folder=folder,
                filename=file_path.name,
                mtime=mtime,
                content_hash=content_hash,
            )
