"""Bloom taxonomy levels used for OHCC scaffolding."""

from __future__ import annotations

from enum import Enum


class BloomLevel(str, Enum):
    """First three Bloom levels for preschool / primary coaching."""

    REMEMBER = "remember"  # Nhận biết — quân nào đang bị đe dọa
    APPLY = "apply"  # Áp dụng — tìm nước chiếu hoặc bắt quân
    ANALYZE = "analyze"  # Phân tích — đánh giá cấu trúc sau đổi quân


BLOOM_VAULT_DIRS: dict[BloomLevel, str] = {
    BloomLevel.REMEMBER: "03-puzzles/bloom-remember",
    BloomLevel.APPLY: "03-puzzles/bloom-apply",
    BloomLevel.ANALYZE: "03-puzzles/bloom-analyze",
}
