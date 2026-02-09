"""Chunking logic for splitting documents by headings."""

import re
from dataclasses import dataclass

from vibe_mcp.indexer.parser import strip_frontmatter

# Maximum characters per chunk (~1500 tokens)
MAX_CHUNK_CHARS = 6000

# Priority headings that get boosted in search
PRIORITY_HEADINGS = {
    "current status",
    "next",
    "next steps",
    "blockers",
    "blocked by",
    "decisions",
}


@dataclass
class Chunk:
    """A chunk of document content."""

    heading: str | None
    heading_level: int
    content: str
    chunk_order: int
    char_offset: int
    is_priority_heading: bool


def is_priority_heading(heading: str | None) -> bool:
    """Check if a heading is a priority heading."""
    if not heading:
        return False
    # Extract just the text, removing # symbols
    text = re.sub(r"^#+\s*", "", heading).strip().lower()
    return text in PRIORITY_HEADINGS


def split_by_headings(content: str) -> list[tuple[str | None, int, str, int]]:
    """
    Split content by level 1 and 2 headings.

    Returns list of (heading, level, section_content, char_offset).
    """
    # Pattern to match # or ## at start of line
    heading_pattern = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)

    sections: list[tuple[str | None, int, str, int]] = []
    last_end = 0
    last_heading: str | None = None
    last_level = 0

    for match in heading_pattern.finditer(content):
        # Capture content before this heading
        if match.start() > last_end:
            section_content = content[last_end : match.start()].strip()
            if section_content or last_heading:
                sections.append(
                    (last_heading, last_level, section_content, last_end)
                )

        # Start a new section
        hashes = match.group(1)
        heading_text = match.group(2).strip()
        last_heading = f"{hashes} {heading_text}"
        last_level = len(hashes)
        last_end = match.end() + 1  # +1 for newline

    # Capture remaining content after last heading
    if last_end < len(content):
        section_content = content[last_end:].strip()
        if section_content or last_heading:
            sections.append((last_heading, last_level, section_content, last_end))
    elif last_heading and not sections:
        # Only a heading, no content after
        sections.append((last_heading, last_level, "", last_end))

    # If no headings found, return entire content as one section
    if not sections:
        sections.append((None, 0, content.strip(), 0))

    return sections


def split_by_paragraphs(content: str, max_chars: int) -> list[str]:
    """Split content into chunks by paragraphs, respecting max_chars."""
    paragraphs = re.split(r"\n\n+", content)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_length = len(para)

        # If single paragraph exceeds limit, split by lines
        if para_length > max_chars:
            # Flush current chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            # Split large paragraph by lines
            line_chunks = split_by_lines(para, max_chars)
            chunks.extend(line_chunks)
            continue

        # Check if adding this paragraph exceeds limit
        new_length = current_length + para_length + (2 if current_chunk else 0)
        if new_length > max_chars and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(para)
        current_length += para_length + (2 if len(current_chunk) > 1 else 0)

    # Flush remaining
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def split_by_lines(content: str, max_chars: int) -> list[str]:
    """Split content by lines, respecting max_chars."""
    lines = content.split("\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for line in lines:
        line_length = len(line)

        # Truncate extremely long lines (edge case)
        if line_length > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            chunks.append(line[:max_chars])
            continue

        new_length = current_length + line_length + (1 if current_chunk else 0)
        if new_length > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(line)
        current_length += line_length + (1 if len(current_chunk) > 1 else 0)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def chunk_document(content: str) -> list[Chunk]:
    """
    Chunk a document by headings.

    Rules:
    1. Split by # and ## headings
    2. If a section exceeds MAX_CHUNK_CHARS, split by paragraphs
    3. If a paragraph exceeds limit, split by lines
    4. If a line exceeds limit, truncate
    """
    # Remove frontmatter first
    body = strip_frontmatter(content)

    # Split by headings
    sections = split_by_headings(body)

    chunks: list[Chunk] = []
    chunk_order = 0

    for heading, level, section_content, char_offset in sections:
        if len(section_content) <= MAX_CHUNK_CHARS:
            # Section fits in one chunk
            chunks.append(
                Chunk(
                    heading=heading,
                    heading_level=level,
                    content=section_content,
                    chunk_order=chunk_order,
                    char_offset=char_offset,
                    is_priority_heading=is_priority_heading(heading),
                )
            )
            chunk_order += 1
        else:
            # Split large section by paragraphs
            sub_contents = split_by_paragraphs(section_content, MAX_CHUNK_CHARS)
            for i, sub_content in enumerate(sub_contents):
                chunks.append(
                    Chunk(
                        heading=heading if i == 0 else None,
                        heading_level=level if i == 0 else 0,
                        content=sub_content,
                        chunk_order=chunk_order,
                        char_offset=char_offset,  # Approximate for sub-chunks
                        is_priority_heading=is_priority_heading(heading) if i == 0 else False,
                    )
                )
                chunk_order += 1

    return chunks
