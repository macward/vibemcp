"""Tests for the SQLite database module."""

import tempfile
from pathlib import Path

import pytest

from vibe_mcp.indexer.database import Database
from vibe_mcp.indexer.models import Chunk, Document


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = Database(db_path)
        database.initialize()
        yield database
        database.close()


class TestDatabaseInitialization:
    def test_creates_database_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            db.initialize()
            assert db_path.exists()
            db.close()

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dir" / "test.db"
            db = Database(db_path)
            db.initialize()
            assert db_path.exists()
            db.close()


class TestProjectOperations:
    def test_create_project(self, db: Database):
        project_id = db.get_or_create_project("test-project", "/path/to/test-project")
        assert project_id > 0

    def test_get_existing_project(self, db: Database):
        id1 = db.get_or_create_project("test", "/path")
        id2 = db.get_or_create_project("test", "/path")
        assert id1 == id2

    def test_get_project_by_name(self, db: Database):
        db.get_or_create_project("my-project", "/path/to/project")
        project = db.get_project("my-project")

        assert project is not None
        assert project.name == "my-project"
        assert project.path == "/path/to/project"

    def test_get_nonexistent_project(self, db: Database):
        project = db.get_project("nonexistent")
        assert project is None

    def test_list_projects(self, db: Database):
        db.get_or_create_project("project-a", "/a")
        db.get_or_create_project("project-b", "/b")

        projects = db.list_projects()
        names = [p.name for p in projects]

        assert "project-a" in names
        assert "project-b" in names


class TestDocumentOperations:
    @pytest.fixture
    def project_id(self, db: Database) -> int:
        return db.get_or_create_project("test-project", "/test")

    def test_upsert_new_document(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/tasks/001-test.md",
            folder="tasks",
            filename="001-test.md",
            type="task",
            status="pending",
            content_hash="abc123",
            mtime=1234567890.0,
        )

        doc_id = db.upsert_document(doc)
        assert doc_id > 0

    def test_upsert_updates_existing(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/tasks/001-test.md",
            folder="tasks",
            filename="001-test.md",
            type="task",
            status="pending",
            content_hash="abc123",
            mtime=1234567890.0,
        )

        id1 = db.upsert_document(doc)

        doc.status = "done"
        doc.content_hash = "xyz789"
        id2 = db.upsert_document(doc)

        assert id1 == id2

        updated = db.get_document_by_path(doc.path)
        assert updated is not None
        assert updated.status == "done"
        assert updated.content_hash == "xyz789"

    def test_get_document_by_path(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/tasks/001-test.md",
            folder="tasks",
            filename="001-test.md",
            type="task",
            status="pending",
            content_hash="hash",
            mtime=1234567890.0,
        )
        db.upsert_document(doc)

        result = db.get_document_by_path("test-project/tasks/001-test.md")
        assert result is not None
        assert result.filename == "001-test.md"

    def test_get_document_hash(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/file.md",
            folder="",
            filename="file.md",
            content_hash="expected_hash",
            mtime=1234567890.0,
        )
        db.upsert_document(doc)

        result = db.get_document_hash("test-project/file.md")
        assert result == "expected_hash"

    def test_get_document_mtime(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/file.md",
            folder="",
            filename="file.md",
            content_hash="hash",
            mtime=1234567890.123,
        )
        db.upsert_document(doc)

        result = db.get_document_mtime("test-project/file.md")
        assert result == pytest.approx(1234567890.123)

    def test_delete_document(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/file.md",
            folder="",
            filename="file.md",
            content_hash="hash",
            mtime=1234567890.0,
        )
        db.upsert_document(doc)

        db.delete_document("test-project/file.md")
        result = db.get_document_by_path("test-project/file.md")
        assert result is None

    def test_list_documents_all(self, db: Database, project_id: int):
        for i in range(3):
            doc = Document(
                project_id=project_id,
                path=f"test-project/tasks/00{i}.md",
                folder="tasks",
                filename=f"00{i}.md",
                content_hash=f"hash{i}",
                mtime=1234567890.0,
            )
            db.upsert_document(doc)

        docs = db.list_documents()
        assert len(docs) == 3

    def test_list_documents_by_project(self, db: Database):
        id1 = db.get_or_create_project("project-a", "/a")
        id2 = db.get_or_create_project("project-b", "/b")

        db.upsert_document(Document(project_id=id1, path="project-a/file.md", folder="", filename="file.md", content_hash="h", mtime=1.0))
        db.upsert_document(Document(project_id=id2, path="project-b/file.md", folder="", filename="file.md", content_hash="h", mtime=1.0))

        docs = db.list_documents(project_name="project-a")
        assert len(docs) == 1
        assert docs[0].path == "project-a/file.md"

    def test_list_documents_by_folder(self, db: Database, project_id: int):
        db.upsert_document(Document(project_id=project_id, path="test-project/tasks/001.md", folder="tasks", filename="001.md", content_hash="h", mtime=1.0))
        db.upsert_document(Document(project_id=project_id, path="test-project/plans/plan.md", folder="plans", filename="plan.md", content_hash="h", mtime=1.0))

        docs = db.list_documents(folder="tasks")
        assert len(docs) == 1
        assert docs[0].folder == "tasks"

    def test_tags_stored_and_retrieved(self, db: Database, project_id: int):
        doc = Document(
            project_id=project_id,
            path="test-project/file.md",
            folder="",
            filename="file.md",
            tags=["python", "mcp", "indexer"],
            content_hash="hash",
            mtime=1234567890.0,
        )
        db.upsert_document(doc)

        result = db.get_document_by_path("test-project/file.md")
        assert result is not None
        assert result.tags == ["python", "mcp", "indexer"]


class TestChunkOperations:
    @pytest.fixture
    def document_id(self, db: Database) -> int:
        project_id = db.get_or_create_project("test", "/test")
        return db.upsert_document(Document(
            project_id=project_id,
            path="test/file.md",
            folder="",
            filename="file.md",
            content_hash="hash",
            mtime=1234567890.0,
        ))

    def test_insert_and_get_chunks(self, db: Database, document_id: int):
        chunks = [
            Chunk(document_id=document_id, heading="# Title", heading_level=1, content="Intro", chunk_order=0, char_offset=0, is_priority_heading=False),
            Chunk(document_id=document_id, heading="## Section", heading_level=2, content="Content", chunk_order=1, char_offset=100, is_priority_heading=False),
        ]

        db.insert_chunks(document_id, chunks)
        result = db.get_chunks(document_id)

        assert len(result) == 2
        assert result[0].heading == "# Title"
        assert result[1].heading == "## Section"

    def test_delete_chunks_for_document(self, db: Database, document_id: int):
        chunks = [Chunk(document_id=document_id, content="Test", chunk_order=0, char_offset=0)]
        db.insert_chunks(document_id, chunks)

        db.delete_chunks_for_document(document_id)
        result = db.get_chunks(document_id)
        assert len(result) == 0

    def test_chunk_order_preserved(self, db: Database, document_id: int):
        chunks = [
            Chunk(document_id=document_id, content="Third", chunk_order=2, char_offset=200),
            Chunk(document_id=document_id, content="First", chunk_order=0, char_offset=0),
            Chunk(document_id=document_id, content="Second", chunk_order=1, char_offset=100),
        ]
        db.insert_chunks(document_id, chunks)

        result = db.get_chunks(document_id)
        assert [c.content for c in result] == ["First", "Second", "Third"]


class TestSearch:
    @pytest.fixture
    def indexed_db(self, db: Database) -> Database:
        project_id = db.get_or_create_project("test-project", "/test")

        # Create documents
        doc1_id = db.upsert_document(Document(
            project_id=project_id,
            path="test-project/tasks/001-auth.md",
            folder="tasks",
            filename="001-auth.md",
            type="task",
            status="in-progress",
            content_hash="h1",
            mtime=1234567890.0,
        ))

        doc2_id = db.upsert_document(Document(
            project_id=project_id,
            path="test-project/references/jwt.md",
            folder="references",
            filename="jwt.md",
            type="reference",
            content_hash="h2",
            mtime=1234567890.0,
        ))

        # Create chunks
        db.insert_chunks(doc1_id, [
            Chunk(document_id=doc1_id, heading="# Auth Task", content="Implement JWT authentication", chunk_order=0, char_offset=0),
            Chunk(document_id=doc1_id, heading="## Next Steps", content="Add token validation", chunk_order=1, char_offset=50, is_priority_heading=True),
        ])

        db.insert_chunks(doc2_id, [
            Chunk(document_id=doc2_id, heading="# JWT Reference", content="JWT is a token format for authentication", chunk_order=0, char_offset=0),
        ])

        return db

    def test_basic_search(self, indexed_db: Database):
        results = indexed_db.search("JWT")
        assert len(results) > 0
        assert any("JWT" in r.content or "JWT" in (r.heading or "") for r in results)

    def test_search_returns_snippet(self, indexed_db: Database):
        results = indexed_db.search("JWT")
        assert len(results) > 0

        result = results[0]
        # Snippet should exist and contain highlighted match
        assert result.snippet is not None
        assert ">>>" in result.snippet and "<<<" in result.snippet
        # JWT should be highlighted in the snippet
        assert ">>>JWT<<<" in result.snippet or "JWT" in result.snippet

    def test_snippet_shows_context(self, indexed_db: Database):
        results = indexed_db.search("authentication")
        assert len(results) > 0

        result = results[0]
        # Snippet should have highlighted text
        assert ">>>" in result.snippet
        assert "<<<" in result.snippet
        # Snippet should contain the search term highlighted
        assert ">>>authentication<<<" in result.snippet

    def test_search_returns_ranking_info(self, indexed_db: Database):
        results = indexed_db.search("authentication")
        assert len(results) > 0

        result = results[0]
        assert result.bm25_score != 0
        assert result.type_boost > 0
        assert result.recency_boost > 0
        assert result.final_score != 0

    def test_search_boosts_tasks_over_references(self, indexed_db: Database):
        results = indexed_db.search("authentication")

        task_result = next((r for r in results if r.folder == "tasks"), None)
        ref_result = next((r for r in results if r.folder == "references"), None)

        if task_result and ref_result:
            assert task_result.type_boost > ref_result.type_boost

    def test_search_boosts_priority_headings(self, indexed_db: Database):
        results = indexed_db.search("token")

        priority_result = next((r for r in results if r.heading and "Next Steps" in r.heading), None)
        if priority_result:
            assert priority_result.heading_boost > 1.0

    def test_search_with_project_filter(self, indexed_db: Database):
        # Add another project
        project_id2 = indexed_db.get_or_create_project("other-project", "/other")
        doc_id = indexed_db.upsert_document(Document(
            project_id=project_id2,
            path="other-project/file.md",
            folder="",
            filename="file.md",
            content_hash="h3",
            mtime=1234567890.0,
        ))
        indexed_db.insert_chunks(doc_id, [
            Chunk(document_id=doc_id, content="JWT in other project", chunk_order=0, char_offset=0),
        ])

        results = indexed_db.search("JWT", project_name="test-project")
        assert all(r.project_name == "test-project" for r in results)

    def test_search_limit(self, indexed_db: Database):
        results = indexed_db.search("authentication", limit=1)
        assert len(results) <= 1


class TestClear:
    def test_clear_removes_all_data(self, db: Database):
        project_id = db.get_or_create_project("test", "/test")
        doc_id = db.upsert_document(Document(
            project_id=project_id,
            path="test/file.md",
            folder="",
            filename="file.md",
            content_hash="hash",
            mtime=1234567890.0,
        ))
        db.insert_chunks(doc_id, [Chunk(document_id=doc_id, content="Test", chunk_order=0, char_offset=0)])

        db.clear()

        assert db.list_projects() == []
        assert db.list_documents() == []
