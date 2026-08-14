"""Bloom level mapping tests."""

from ohcc.scaffolding.bloom import BLOOM_VAULT_DIRS, BloomLevel


def test_vault_dirs_cover_three_levels() -> None:
    assert set(BLOOM_VAULT_DIRS) == {
        BloomLevel.REMEMBER,
        BloomLevel.APPLY,
        BloomLevel.ANALYZE,
    }
    assert "bloom-remember" in BLOOM_VAULT_DIRS[BloomLevel.REMEMBER]
