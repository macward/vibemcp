"""Tests for the main Indexer class."""

import tempfile
from pathlib import Path

import pytest

from vibe_mcp.indexer import Indexer


@pytest.fixture
def fixtures_root() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def indexer(fixtures_root: Path):
    """Create an indexer with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        idx = Indexer(vibe_root=fixtures_root, db_path=db_path)
        idx.initialize()
        yield idx
        idx.close()


class TestIndexerReindex:
    def test_reindex_all(self, indexer: Indexer):
        count = indexer.reindex()
        assert count > 0

    def test_reindex_creates_projects(self, indexer: Indexer):
        indexer.reindex()
        projects = indexer.list_projects()
        names = [p.name for p in projects]

        assert "demo-api" in names
        assert "demo-frontend" in names

    def test_reindex_indexes_documents(self, indexer: Indexer):
        indexer.reindex()
        docs = indexer.list_documents()

        # Should have multiple documents
        assert len(docs) > 10

        # Should have various types
        types = {d.type for d in docs}
        assert "task" in types
        assert "plan" in types
        assert "session" in types

    def test_reindex_extracts_status(self, indexer: Indexer):
        indexer.reindex()
        docs = indexer.list_documents(project="demo-api", folder="tasks")

        statuses = {d.status for d in docs}
        assert "done" in statuses
        assert "in-progress" in statuses
        assert "blocked" in statuses
        assert "pending" in statuses


class TestIndexerSync:
    def test_sync_detects_no_changes(self, indexer: Indexer):
        indexer.reindex()
        added, updated, deleted = indexer.sync()

        # No changes since reindex just happened
        assert added == 0
        assert updated == 0
        assert deleted == 0

    def test_sync_detects_new_file(self, indexer: Indexer, fixtures_root: Path):
        # Create a temp vibe root with one project
        with tempfile.TemporaryDirectory() as tmpdir:
            vibe_root = Path(tmpdir)
            project_dir = vibe_root / "test-project"
            project_dir.mkdir()
            tasks_dir = project_dir / "tasks"
            tasks_dir.mkdir()

            # Create one file
            (tasks_dir / "001-first.md").write_text("# First Task\n\nStatus: pending")

            # Create indexer and reindex
            db_path = vibe_root / "index.db"
            idx = Indexer(vibe_root=vibe_root, db_path=db_path)
            idx.reindex()

            # Add new file
            (tasks_dir / "002-second.md").write_text("# Second Task\n\nStatus: pending")

            added, updated, deleted = idx.sync()
            assert added == 1
            assert updated == 0
            assert deleted == 0

            idx.close()

    def test_sync_detects_deleted_file(self, indexer: Indexer):
        with tempfile.TemporaryDirectory() as tmpdir:
            vibe_root = Path(tmpdir)
            project_dir = vibe_root / "test-project"
            tasks_dir = project_dir / "tasks"
            tasks_dir.mkdir(parents=True)

            file1 = tasks_dir / "001-first.md"
            file2 = tasks_dir / "002-second.md"
            file1.write_text("# First")
            file2.write_text("# Second")

            db_path = vibe_root / "index.db"
            idx = Indexer(vibe_root=vibe_root, db_path=db_path)
            idx.reindex()

            # Delete one file
            file2.unlink()

            added, updated, deleted = idx.sync()
            assert added == 0
            assert updated == 0
            assert deleted == 1

            idx.close()


class TestIndexerSearch:
    def test_search_finds_content(self, indexer: Indexer):
        indexer.reindex()
        results = indexer.search("authentication")

        assert len(results) > 0
        # Should find auth-related content
        all_content = " ".join(r.content for r in results)
        assert "auth" in all_content.lower() or "JWT" in all_content

    def test_search_cross_project(self, indexer: Indexer):
        indexer.reindex()
        results = indexer.search("setup")

        projects = {r.project_name for r in results}
        # Both projects have setup-related tasks
        assert len(projects) >= 1

    def test_search_with_project_filter(self, indexer: Indexer):
        indexer.reindex()
        results = indexer.search("setup", project="demo-api")

        assert all(r.project_name == "demo-api" for r in results)

    def test_search_priority_heading_boost(self, indexer: Indexer):
        indexer.reindex()
        # demo-api/status.md has "Blockers" heading
        results = indexer.search("Redis")

        # Should find the blockers section
        blocker_results = [r for r in results if r.heading and "Blocker" in r.heading]
        if blocker_results:
            assert blocker_results[0].heading_boost > 1.0

    def test_search_type_boost(self, indexer: Indexer):
        indexer.reindex()
        results = indexer.search("JWT")

        # Task results should have higher type_boost than reference results
        task_results = [r for r in results if r.folder == "tasks"]
        ref_results = [r for r in results if r.folder == "references"]

        if task_results and ref_results:
            assert task_results[0].type_boost > ref_results[0].type_boost


class TestIndexerListMethods:
    def test_list_projects(self, indexer: Indexer):
        indexer.reindex()
        projects = indexer.list_projects()

        assert len(projects) == 2
        names = {p.name for p in projects}
        assert names == {"demo-api", "demo-frontend"}

    def test_list_documents(self, indexer: Indexer):
        indexer.reindex()
        docs = indexer.list_documents()

        assert len(docs) > 0
        # All docs should have required fields
        for doc in docs:
            assert doc.path
            assert doc.filename
            assert doc.content_hash

    def test_list_documents_by_project(self, indexer: Indexer):
        indexer.reindex()
        docs = indexer.list_documents(project="demo-api")

        assert len(docs) > 0
        assert all("demo-api" in d.path for d in docs)

    def test_list_documents_by_folder(self, indexer: Indexer):
        indexer.reindex()
        docs = indexer.list_documents(folder="tasks")

        assert len(docs) > 0
        assert all(d.folder == "tasks" for d in docs)

    def test_get_document(self, indexer: Indexer):
        indexer.reindex()
        doc = indexer.get_document("demo-api/tasks/001-setup-proyecto.md")

        assert doc is not None
        assert doc.filename == "001-setup-proyecto.md"
        assert doc.type == "task"

    def test_get_chunks(self, indexer: Indexer):
        indexer.reindex()
        doc = indexer.get_document("demo-api/tasks/003-auth-jwt.md")
        assert doc is not None

        chunks = indexer.get_chunks(doc.id)
        assert len(chunks) > 0

        headings = [c.heading for c in chunks if c.heading]
        assert any("Task" in h for h in headings)
        assert any("Objective" in h for h in headings)


class TestIndexerWithFrontmatter:
    def test_parses_frontmatter_metadata(self, indexer: Indexer):
        indexer.reindex()
        doc = indexer.get_document("demo-frontend/tasks/001-setup-vite.md")

        assert doc is not None
        assert doc.owner == "diana"
        assert doc.status == "done"
        assert "vite" in doc.tags

    def test_infers_metadata_without_frontmatter(self, indexer: Indexer):
        indexer.reindex()
        doc = indexer.get_document("demo-api/tasks/001-setup-proyecto.md")

        assert doc is not None
        assert doc.type == "task"
        assert doc.status == "done"  # Inferred from body


class TestIndexerConcurrency:
    def test_multiple_reads_concurrent(self, indexer: Indexer):
        """Test that multiple reads don't block each other."""
        indexer.reindex()

        import concurrent.futures

        def read_docs():
            return indexer.list_documents()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(read_docs) for _ in range(10)]
            results = [f.result() for f in futures]

        # All reads should return the same data
        assert all(len(r) == len(results[0]) for r in results)
