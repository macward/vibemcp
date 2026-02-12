"""Tests for the frontmatter parser."""


from vibe_mcp.indexer.parser import parse_frontmatter, strip_frontmatter


class TestStripFrontmatter:
    def test_strips_yaml_frontmatter(self):
        content = """---
title: Test
---
# Content
Body text"""
        result = strip_frontmatter(content)
        assert result == "# Content\nBody text"

    def test_preserves_content_without_frontmatter(self):
        content = "# No frontmatter\n\nJust content"
        result = strip_frontmatter(content)
        assert result == content

    def test_handles_empty_frontmatter(self):
        content = """---
---
Content"""
        result = strip_frontmatter(content)
        assert result == "Content"

    def test_handles_content_starting_with_triple_dash(self):
        content = "---not frontmatter\ncontent"
        # This won't have a second ---, so it stays as is
        result = strip_frontmatter(content)
        assert result == content


class TestParseFrontmatter:
    def test_parses_yaml_frontmatter(self):
        content = """---
project: my-project
type: task
status: done
updated: 2025-02-09
tags: [foo, bar]
owner: alice
---
# Content"""
        data, body = parse_frontmatter(content, "my-project/tasks/001-test.md")

        assert data.project == "my-project"
        assert data.type == "task"
        assert data.status == "done"
        # updated can be date object or string
        assert str(data.updated) == "2025-02-09"
        assert data.tags == ["foo", "bar"]
        assert data.owner == "alice"
        assert body == "# Content"

    def test_infers_project_from_path(self):
        content = "# Content"
        data, _ = parse_frontmatter(content, "demo-api/tasks/001-test.md")
        assert data.project == "demo-api"

    def test_infers_type_from_folder(self):
        folders = [
            ("tasks", "task"),
            ("plans", "plan"),
            ("sessions", "session"),
            ("reports", "report"),
            ("changelog", "changelog"),
            ("references", "reference"),
            ("scratch", "scratch"),
            ("assets", "asset"),
        ]
        for folder, expected_type in folders:
            content = "# Content"
            data, _ = parse_frontmatter(content, f"project/{folder}/file.md")
            assert data.type == expected_type, f"Expected {expected_type} for {folder}"

    def test_infers_status_type_from_root_file(self):
        content = "# Status"
        data, _ = parse_frontmatter(content, "project/status.md")
        assert data.type == "status"

    def test_extracts_status_from_body(self):
        content = """# Task

Status: in-progress

## Objective"""
        data, _ = parse_frontmatter(content, "project/tasks/001-test.md")
        assert data.status == "in-progress"

    def test_extracts_status_case_insensitive(self):
        content = "STATUS: DONE"
        data, _ = parse_frontmatter(content, "project/tasks/001-test.md")
        assert data.status == "done"

    def test_frontmatter_overrides_inference(self):
        content = """---
type: plan
status: blocked
---
# Content"""
        data, _ = parse_frontmatter(content, "project/tasks/001-test.md")
        assert data.type == "plan"  # From frontmatter, not inferred as "task"
        assert data.status == "blocked"

    def test_handles_invalid_yaml(self):
        content = """---
invalid: [unclosed
---
# Content"""
        data, body = parse_frontmatter(content, "project/tasks/001-test.md")
        # Should not crash, just skip frontmatter parsing
        assert data.type == "task"  # Still inferred from path
        assert "# Content" in body or "invalid" in body  # Content preserved

    def test_handles_non_dict_yaml(self):
        content = """---
- list item
- another
---
# Content"""
        data, body = parse_frontmatter(content, "project/tasks/001-test.md")
        assert data.raw is None  # Not a dict
        assert data.type == "task"  # Inferred

    def test_tags_converted_to_strings(self):
        content = """---
tags: [1, 2, foo]
---
# Content"""
        data, _ = parse_frontmatter(content, "project/tasks/001.md")
        assert data.tags == ["1", "2", "foo"]

    def test_preserves_body_without_frontmatter(self):
        content = """# Title

Status: pending

## Steps

1. First step
2. Second step"""
        data, body = parse_frontmatter(content, "project/tasks/001-test.md")
        assert body == content  # No frontmatter, body is full content
        assert data.status == "pending"  # Extracted from body

    def test_extracts_feature_from_frontmatter(self):
        content = """---
type: task
status: pending
feature: auth
---
# Task: Auth Bearer Token

## Objective
Implement bearer token."""
        data, body = parse_frontmatter(content, "project/tasks/017-auth-bearer.md")
        assert data.feature == "auth"
        assert data.type == "task"
        assert data.status == "pending"

    def test_feature_none_when_not_present(self):
        content = """---
type: task
status: pending
---
# Task: No Feature"""
        data, _ = parse_frontmatter(content, "project/tasks/001-test.md")
        assert data.feature is None
