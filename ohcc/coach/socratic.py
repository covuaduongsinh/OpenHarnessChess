"""Socratic question helpers for CoachAgent / Thầy Tường."""

from __future__ import annotations

from ohcc.scaffolding.bloom import BloomLevel

# Sample stems aligned with the Thầy Tường system prompt.
BLOOM_QUESTION_STEMS: dict[BloomLevel, tuple[str, ...]] = {
    BloomLevel.REMEMBER: (
        "Quân nào của em đang không có bạn bảo vệ?",
        "Em nhìn ô đó: có ai đang nhắm tới quân của em không?",
        "Quân nào đang đứng một mình, chưa có đội giữ?",
    ),
    BloomLevel.APPLY: (
        "Em có nước chiếu hoặc bắt quân nào an toàn không?",
        "Em thử tìm một nước khiến vua đối phương phải xịch đi?",
        "Em che hoặc chạy quân đang bị đe dọa bằng cách nào?",
    ),
    BloomLevel.ANALYZE: (
        "Nếu đổi quân ở đây, vua em có thông thoáng hơn không? Vì sao?",
        "Sau nước đổi này, cánh nào của em chắc hơn?",
        "Em thích cấu trúc tốt sau đổi quân, hay giữ quân để tấn công? Vì sao?",
    ),
}


def build_opening_question(*, bloom_level: str, theme: str) -> str:
    """Return a Socratic opening question for the given Bloom level and theme."""
    try:
        level = BloomLevel(bloom_level)
    except ValueError:
        level = BloomLevel.REMEMBER
    stem = BLOOM_QUESTION_STEMS[level][0]
    theme = theme.strip()
    if not theme:
        return stem
    return f"{stem} (chủ đề: {theme})"


def sample_questions(level: BloomLevel | str, *, limit: int = 3) -> list[str]:
    """Return up to *limit* sample questions for a Bloom level."""
    if isinstance(level, str):
        level = BloomLevel(level)
    return list(BLOOM_QUESTION_STEMS[level][:limit])
