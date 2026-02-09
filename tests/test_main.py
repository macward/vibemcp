"""Tests for main module."""

from main import main


def test_main(capsys):
    """Test main function."""
    main()
    captured = capsys.readouterr()
    assert "Hello from vibemcp!" in captured.out
