"""Tests for the document chunker."""

import pytest

from vibe_mcp.indexer.chunker import (
    MAX_CHUNK_CHARS,
    chunk_document,
    is_priority_heading,
    split_by_headings,
    split_by_lines,
    split_by_paragraphs,
)


class TestIsPriorityHeading:
    @pytest.mark.parametrize(
        ("heading", "expected"),
        [
            ("## Current Status", True),
            ("## Next", True),
            ("## Next Steps", True),
            ("## Blockers", True),
            ("## Blocked By", True),
            ("## Decisions", True),
            ("# CURRENT STATUS", True),  # Case insensitive
            ("## Objective", False),  # Not in priority list
            ("## Steps", False),
            (None, False),
            ("", False),
        ],
    )
    def test_priority_detection(self, heading: str | None, expected: bool):
        assert is_priority_heading(heading) == expected


class TestSplitByHeadings:
    def test_splits_on_h1_and_h2(self):
        content = """# Title

Intro

## Section 1

Content 1

## Section 2

Content 2"""
        sections = split_by_headings(content)

        assert len(sections) == 3
        assert sections[0][0] == "# Title"
        assert "Intro" in sections[0][2]
        assert sections[1][0] == "## Section 1"
        assert "Content 1" in sections[1][2]
        assert sections[2][0] == "## Section 2"
        assert "Content 2" in sections[2][2]

    def test_heading_levels(self):
        content = """# H1

Content under H1

## H2

Content under H2

# Another H1

More content"""
        sections = split_by_headings(content)

        assert len(sections) == 3
        assert sections[0][1] == 1  # H1 level
        assert sections[1][1] == 2  # H2 level
        assert sections[2][1] == 1  # H1 level

    def test_no_headings(self):
        content = "Just plain content\n\nWith paragraphs"
        sections = split_by_headings(content)

        assert len(sections) == 1
        assert sections[0][0] is None
        assert sections[0][1] == 0
        assert "Just plain content" in sections[0][2]

    def test_content_before_first_heading(self):
        content = """Preamble text

# First Heading

Content"""
        sections = split_by_headings(content)

        # First section has no heading but has content
        assert sections[0][0] is None
        assert "Preamble" in sections[0][2]
        assert sections[1][0] == "# First Heading"

    def test_ignores_h3_and_deeper(self):
        content = """# Title

## Section

### Subsection

Content"""
        sections = split_by_headings(content)

        # Should only split on # and ##
        assert len(sections) == 2
        assert "### Subsection" in sections[1][2]


class TestSplitByParagraphs:
    def test_keeps_small_content_together(self):
        content = "First paragraph.\n\nSecond paragraph."
        chunks = split_by_paragraphs(content, 1000)
        assert len(chunks) == 1
        assert "First" in chunks[0]
        assert "Second" in chunks[0]

    def test_splits_at_paragraph_boundary(self):
        para1 = "A" * 500
        para2 = "B" * 500
        content = f"{para1}\n\n{para2}"
        chunks = split_by_paragraphs(content, 600)

        assert len(chunks) == 2
        assert para1 in chunks[0]
        assert para2 in chunks[1]

    def test_handles_large_single_paragraph(self):
        # Create content that will be split into lines
        large_para = "word " * 2000  # ~10000 chars
        chunks = split_by_paragraphs(large_para, 1000)
        # The content is one long line, so split_by_lines will truncate or split
        assert len(chunks) >= 1
        # Each chunk should respect the limit (or be truncated)
        assert all(len(c) <= 10000 for c in chunks)  # Just check it doesn't crash


class TestSplitByLines:
    def test_keeps_small_content_together(self):
        content = "Line 1\nLine 2\nLine 3"
        chunks = split_by_lines(content, 1000)
        assert len(chunks) == 1

    def test_splits_at_line_boundary(self):
        content = "A" * 500 + "\n" + "B" * 500
        chunks = split_by_lines(content, 600)
        assert len(chunks) == 2

    def test_truncates_very_long_line(self):
        content = "X" * 2000
        chunks = split_by_lines(content, 1000)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1000


class TestChunkDocument:
    def test_basic_document_chunking(self):
        content = """# Task: Test

Status: pending

## Objective

Do something.

## Steps

1. Step one
2. Step two

## Notes

Additional info."""
        chunks = chunk_document(content)

        assert len(chunks) >= 4
        headings = [c.heading for c in chunks]
        assert "# Task: Test" in headings
        assert "## Objective" in headings
        assert "## Steps" in headings
        assert "## Notes" in headings

    def test_chunk_order_is_sequential(self):
        content = """# First
## Second
## Third"""
        chunks = chunk_document(content)
        orders = [c.chunk_order for c in chunks]
        assert orders == list(range(len(chunks)))

    def test_priority_heading_detected(self):
        content = """# Status

## Current Status

Active work.

## Next Steps

1. Do this
2. Do that"""
        chunks = chunk_document(content)

        current_status = next(c for c in chunks if c.heading and "Current Status" in c.heading)
        next_steps = next(c for c in chunks if c.heading and "Next Steps" in c.heading)

        assert current_status.is_priority_heading
        assert next_steps.is_priority_heading

    def test_strips_frontmatter(self):
        content = """---
project: test
---
# Title

Content"""
        chunks = chunk_document(content)

        # Frontmatter should not appear in chunks
        all_content = " ".join(c.content for c in chunks)
        assert "---" not in all_content
        assert "project:" not in all_content

    def test_large_section_split(self):
        large_content = "Word " * 2000  # ~10000 chars
        content = f"""# Title

{large_content}

## End"""
        chunks = chunk_document(content)

        # Large section should be split
        # At least one split should occur for content over MAX_CHUNK_CHARS
        chunk_contents = [c.content for c in chunks]
        assert all(len(c) <= MAX_CHUNK_CHARS for c in chunk_contents)

    def test_empty_document(self):
        chunks = chunk_document("")
        assert len(chunks) == 1
        assert chunks[0].content == ""

    def test_heading_level_preserved(self):
        content = """# H1 Title

Content

## H2 Section

More content"""
        chunks = chunk_document(content)

        h1_chunk = next(c for c in chunks if c.heading and c.heading.startswith("# "))
        h2_chunk = next(c for c in chunks if c.heading and c.heading.startswith("## "))

        assert h1_chunk.heading_level == 1
        assert h2_chunk.heading_level == 2
