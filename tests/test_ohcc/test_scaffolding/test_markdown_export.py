"""Markdown export smoke tests."""

from ohcc.scaffolding.markdown_export import render_puzzle_markdown


def test_render_includes_frontmatter_and_fen() -> None:
    md = render_puzzle_markdown(
        title="Quân treo",
        fen="8/8/8/8/8/8/8/4K2k w - - 0 1",
        bloom="remember",
        prompt="Quân nào đang bị đe dọa?",
    )
    assert "type: scaffolding-puzzle" in md
    assert "bloom: remember" in md
    assert "8/8/8/8/8/8/8/4K2k" in md
    assert "# Quân treo" in md
