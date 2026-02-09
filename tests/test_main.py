"""Tests for main module."""

from vibe_mcp.main import main


def test_main(capsys):
    """Test main function prints startup message."""
    main()
    captured = capsys.readouterr()
    assert "vibemcp starting" in captured.out
    assert "VIBE_ROOT" in captured.out
