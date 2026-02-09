"""MCP tools for vibeMCP server.

This module defines the tools exposed by the MCP server:
- search: Full-text search across all projects using FTS5
- read_doc: Read a complete document by path
- list_tasks: List tasks from a project or cross-project
- get_plan: Read execution plan for a project
"""

from fastmcp import FastMCP

from vibe_mcp.config import get_config
from vibe_mcp.indexer import Database


def register_tools(mcp: FastMCP, db: Database) -> None:
    """Register all read tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance
        db: Database instance for queries
    """

    @mcp.tool()
    def search(
        query: str,
        project: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search for content across all projects using full-text search.

        Uses SQLite FTS5 with intelligent ranking that considers:
        - BM25 relevance score
        - Document type (tasks, plans, sessions prioritized)
        - Recency (recent documents score higher)
        - Heading importance (priority headings boosted)
        - Task status (in-progress tasks prioritized)

        Args:
            query: Search query (FTS5 syntax supported)
            project: Optional project name to filter results
            limit: Maximum number of results to return (default: 20)

        Returns:
            List of search results with:
            - project_name: Name of the project
            - document_path: Path to the document
            - folder: Folder containing the document (tasks/plans/sessions/etc)
            - heading: Section heading where match was found
            - snippet: Contextual snippet with matches highlighted (>>>match<<<)
            - score: Relevance score (higher is better)
        """
        results = db.search(query=query, project_name=project, limit=limit)

        return [
            {
                "project_name": result.project_name,
                "document_path": result.document_path,
                "folder": result.folder,
                "heading": result.heading,
                "snippet": result.snippet,
                "score": round(result.final_score, 2),
            }
            for result in results
        ]

    @mcp.tool()
    def read_doc(project: str, path: str) -> dict:
        """Read a complete document from a project.

        Args:
            project: Name of the project
            path: Relative path within the project (e.g., "tasks/001-setup.md")

        Returns:
            Document with:
            - project: Project name
            - path: Document path
            - content: Full document content
            - exists: Whether document was found
            - error: Error message if document not found
        """
        config = get_config()
        full_path = config.vibe_root / project / path

        # Validate path is within VIBE_ROOT (security check)
        try:
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(config.vibe_root.resolve())):
                return {
                    "project": project,
                    "path": path,
                    "content": None,
                    "exists": False,
                    "error": "Path is outside VIBE_ROOT",
                }
        except (ValueError, OSError) as e:
            return {
                "project": project,
                "path": path,
                "content": None,
                "exists": False,
                "error": f"Invalid path: {e}",
            }

        # Check if file exists and read it
        if not full_path.exists():
            return {
                "project": project,
                "path": path,
                "content": None,
                "exists": False,
                "error": "Document not found",
            }

        if not full_path.is_file():
            return {
                "project": project,
                "path": path,
                "content": None,
                "exists": False,
                "error": "Path is not a file",
            }

        try:
            content = full_path.read_text(encoding="utf-8")
            return {
                "project": project,
                "path": path,
                "content": content,
                "exists": True,
                "error": None,
            }
        except Exception as e:
            return {
                "project": project,
                "path": path,
                "content": None,
                "exists": True,
                "error": f"Error reading file: {e}",
            }

    @mcp.tool()
    def list_tasks(
        project: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List tasks from a project or across all projects.

        Args:
            project: Optional project name to filter tasks
            status: Optional status filter (pending/in-progress/done/blocked)

        Returns:
            List of tasks with:
            - project_name: Name of the project
            - path: Path to task file
            - filename: Task filename
            - status: Task status (pending/in-progress/done/blocked/null)
            - owner: Task owner (if assigned)
            - updated: Last update date (if available)
        """
        # Use raw SQL query to join projects and documents for efficiency
        query = """
            SELECT
                p.name as project_name,
                d.path,
                d.filename,
                d.status,
                d.owner,
                d.updated
            FROM documents d
            JOIN projects p ON d.project_id = p.id
            WHERE d.folder = 'tasks'
        """
        params: list = []

        if project:
            query += " AND p.name = ?"
            params.append(project)

        if status:
            query += " AND d.status = ?"
            params.append(status)

        query += " ORDER BY d.path"

        # Execute query using database's read cursor
        with db._read_cursor() as cursor:
            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "project_name": row["project_name"],
                    "path": row["path"],
                    "filename": row["filename"],
                    "status": row["status"],
                    "owner": row["owner"],
                    "updated": row["updated"],
                })

        return results

    @mcp.tool()
    def get_plan(project: str) -> dict:
        """Read the execution plan for a project.

        Args:
            project: Name of the project

        Returns:
            Plan document with:
            - project: Project name
            - content: Plan content (if exists)
            - exists: Whether plan was found
        """
        config = get_config()
        plan_path = config.vibe_root / project / "plans" / "execution-plan.md"

        if not plan_path.exists():
            return {
                "project": project,
                "content": None,
                "exists": False,
            }

        try:
            content = plan_path.read_text(encoding="utf-8")
            return {
                "project": project,
                "content": content,
                "exists": True,
            }
        except Exception as e:
            return {
                "project": project,
                "content": None,
                "exists": False,
                "error": f"Error reading plan: {e}",
            }
