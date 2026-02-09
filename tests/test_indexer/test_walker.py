"""Tests for the file walker."""

from pathlib import Path

import pytest

from vibe_mcp.indexer.walker import FileInfo, compute_hash, walk_vibe_root


class TestComputeHash:
    def test_computes_sha256(self):
        content = b"hello world"
        result = compute_hash(content)
        assert result == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_different_content_different_hash(self):
        assert compute_hash(b"foo") != compute_hash(b"bar")

    def test_same_content_same_hash(self):
        assert compute_hash(b"same") == compute_hash(b"same")


class TestWalkVibeRoot:
    @pytest.fixture
    def fixtures_root(self) -> Path:
        return Path(__file__).parent.parent / "fixtures"

    def test_discovers_all_markdown_files(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        assert len(files) > 0
        assert all(f.filename.endswith(".md") for f in files)

    def test_discovers_demo_api_tasks(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        demo_api_tasks = [f for f in files if f.project_name == "demo-api" and f.folder == "tasks"]
        assert len(demo_api_tasks) == 5

    def test_discovers_demo_frontend_tasks(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        demo_frontend_tasks = [f for f in files if f.project_name == "demo-frontend" and f.folder == "tasks"]
        assert len(demo_frontend_tasks) == 4

    def test_discovers_root_status_file(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        status_files = [f for f in files if f.filename == "status.md"]
        assert len(status_files) == 2  # One per project

    def test_file_info_has_required_fields(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        assert len(files) > 0

        f = files[0]
        assert isinstance(f, FileInfo)
        assert f.path.exists()
        assert f.relative_path
        assert f.project_name
        assert f.filename.endswith(".md")
        assert f.mtime > 0
        assert len(f.content_hash) == 64  # SHA-256 hex

    def test_relative_path_format(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        for f in files:
            parts = f.relative_path.split("/")
            assert len(parts) >= 2  # project/filename or project/folder/filename
            assert parts[0] == f.project_name

    def test_folder_empty_for_root_files(self, fixtures_root: Path):
        files = list(walk_vibe_root(fixtures_root))
        status_files = [f for f in files if f.filename == "status.md"]
        for f in status_files:
            assert f.folder == ""

    def test_skips_hidden_directories(self, fixtures_root: Path, tmp_path: Path):
        # Create a vibe root with hidden directory
        project = tmp_path / "test-project"
        project.mkdir()
        (project / "tasks").mkdir()
        (project / ".hidden").mkdir()
        (project / "tasks" / "001-test.md").write_text("# Test")
        (project / ".hidden" / "secret.md").write_text("# Secret")

        files = list(walk_vibe_root(tmp_path))
        paths = [f.relative_path for f in files]
        assert "test-project/tasks/001-test.md" in paths
        assert "test-project/.hidden/secret.md" not in paths

    def test_handles_nonexistent_root(self):
        files = list(walk_vibe_root(Path("/nonexistent/path")))
        assert files == []
