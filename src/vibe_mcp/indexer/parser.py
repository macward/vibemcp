"""Parser for YAML frontmatter with fallback to path inference."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FrontmatterData:
    """Parsed frontmatter data."""

    project: str | None = None
    type: str | None = None
    status: str | None = None
    updated: str | None = None
    tags: list[str] | None = None
    owner: str | None = None
    feature: str | None = None
    raw: dict | None = None


# Mapping from folder name to document type
FOLDER_TYPE_MAP = {
    "tasks": "task",
    "plans": "plan",
    "sessions": "session",
    "reports": "report",
    "changelog": "changelog",
    "references": "reference",
    "scratch": "scratch",
    "assets": "asset",
}

# Status pattern for task files
STATUS_PATTERN = re.compile(r"^Status:\s*(\S+)", re.MULTILINE | re.IGNORECASE)


def parse_frontmatter(content: str, file_path: str) -> tuple[FrontmatterData, str]:
    """
    Parse YAML frontmatter from markdown content.

    If frontmatter is not present, infers metadata from path.

    Args:
        content: The full markdown content
        file_path: Relative path from VIBE_ROOT (e.g., "project/tasks/001-foo.md")

    Returns:
        Tuple of (FrontmatterData, content_without_frontmatter)
    """
    data = FrontmatterData()
    body = content

    # Try to extract frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                raw = yaml.safe_load(parts[1])
                if isinstance(raw, dict):
                    data.raw = raw
                    data.project = raw.get("project")
                    data.type = raw.get("type")
                    data.status = raw.get("status")
                    # Handle updated field - could be date or string
                    updated = raw.get("updated")
                    if updated is not None:
                        data.updated = str(updated)
                    data.owner = raw.get("owner")
                    data.feature = raw.get("feature")

                    tags = raw.get("tags")
                    if isinstance(tags, list):
                        data.tags = [str(t) for t in tags]

                    # Body is everything after the closing ---
                    body = parts[2].lstrip("\n")
            except yaml.YAMLError as e:
                logger.debug("Invalid YAML frontmatter in %s: %s", file_path, e)

    # Infer from path if not set
    path_parts = Path(file_path).parts
    if len(path_parts) >= 2:
        # First part is project, second is folder or file
        if data.project is None:
            data.project = path_parts[0]

        if len(path_parts) >= 2:
            # Second part could be folder (tasks/) or root file (status.md)
            potential_folder = path_parts[1]
            if not potential_folder.endswith(".md"):
                # It's a folder
                if data.type is None and potential_folder in FOLDER_TYPE_MAP:
                    data.type = FOLDER_TYPE_MAP[potential_folder]
            else:
                # Root file like status.md
                if potential_folder == "status.md":
                    data.type = "status"

    # Try to extract status from body for task files
    if data.type == "task" and data.status is None:
        match = STATUS_PATTERN.search(body if body else content)
        if match:
            data.status = match.group(1).lower()

    return data, body


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return content
