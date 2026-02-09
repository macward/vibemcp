"""Example MCP server demonstrating resource usage.

This example shows how to create an MCP server with the vibe resources.
Run with: uv run python examples/example_server.py
"""

from fastmcp import FastMCP

from vibe_mcp.resources import register_resources

# Create MCP server
mcp = FastMCP("vibe-mcp-example")

# Register resources
register_resources(mcp)

# Example: Add a simple tool that uses resources
@mcp.tool()
def list_project_tasks(project_name: str) -> str:
    """List all tasks for a given project.

    Args:
        project_name: Name of the project

    Returns:
        A summary of the project's tasks
    """
    from vibe_mcp.resources import get_project_detail_resource

    try:
        return get_project_detail_resource(project_name)
    except ValueError as e:
        return f"Error: {e}"


if __name__ == "__main__":
    # Run the server
    print("Starting vibe-mcp example server...")
    print("\nAvailable resources:")
    print("  - vibe://projects")
    print("  - vibe://projects/{name}")
    print("  - vibe://projects/{name}/{folder}/{file}")
    print("\nAvailable tools:")
    print("  - list_project_tasks")
    print("\nPress Ctrl+C to stop")

    # This would normally be run by the MCP client
    # For testing, you can use: mcp.run()
    mcp.run()
