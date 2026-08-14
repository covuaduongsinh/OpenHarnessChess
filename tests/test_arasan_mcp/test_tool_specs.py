"""arasan-mcp tool catalog smoke tests."""

from arasan_mcp.tools import TOOL_SPECS


def test_tool_specs_non_empty() -> None:
    names = {t["name"] for t in TOOL_SPECS}
    assert "analyze_fen" in names
    assert "evaluate_position" in names
    assert "compare_positions" in names
