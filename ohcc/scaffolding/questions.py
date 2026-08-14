"""Socratic question generation for Bloom scaffolding puzzles."""

from __future__ import annotations

from ohcc.chess_core.heuristics.hanging import find_hanging_pieces
from ohcc.scaffolding.bloom import BloomLevel
from ohcc.scaffolding.mistake_detect import TeachingMoment


def questions_for_moment(
    moment: TeachingMoment,
    *,
    student_level: str = "primary",
) -> dict[BloomLevel, str]:
    """Return one Socratic prompt per Bloom level for a teaching moment."""
    hanging = find_hanging_pieces(moment.fen)
    hanging_hint = hanging[0] if hanging else None
    kind = moment.kind

    if student_level == "preschool":
        remember = _preschool_remember(kind, hanging_hint)
        apply_q = _preschool_apply(kind)
        analyze = _preschool_analyze(kind)
    else:
        remember = _primary_remember(kind, hanging_hint, moment)
        apply_q = _primary_apply(kind, moment)
        analyze = _primary_analyze(kind, moment)

    return {
        BloomLevel.REMEMBER: remember,
        BloomLevel.APPLY: apply_q,
        BloomLevel.ANALYZE: analyze,
    }


def _preschool_remember(kind: str, hanging: str | None) -> str:
    if hanging:
        return (
            f"Em nhìn bàn cờ: quân trên ô **{hanging}** có **bạn giữ** không, "
            "hay đang đứng một mình?"
        )
    if kind == "check":
        return "Em nhìn vua: có quân nào đang **nhăm nhe** tới vua không?"
    if kind == "eval_drop":
        return "Sau nước vừa rồi, em thấy chỗ nào trên bàn **kém vui** hơn trước?"
    return "Em nhìn quanh: quân nào của mình trông **nguy hiểm** nhất?"


def _preschool_apply(kind: str) -> str:
    if kind in {"check", "mate"}:
        return "Em thử tìm một nước khiến vua đối phương **phải xịch đi** nhé?"
    if kind == "capture":
        return "Em có thấy quân nào **bắt được** mà vẫn an toàn không?"
    if kind == "eval_drop":
        return "Em muốn **che**, **chạy**, hay **đổi** để bàn cờ chắc hơn?"
    return "Em muốn **che**, **chạy**, hay **bắt** để giúp quân đang nguy hiểm?"


def _preschool_analyze(kind: str) -> str:
    _ = kind
    return (
        "Nếu em đổi quân ở chỗ này, vua em có **thông thoáng** hơn không? "
        "Em nói thầy nghe vì sao."
    )


def _primary_remember(kind: str, hanging: str | None, moment: TeachingMoment) -> str:
    if hanging:
        return (
            f"Quân nào đang **không có bạn bảo vệ**? "
            f"(Gợi ý vùng: ô gần **{hanging}** — em tự chỉ ra.)"
        )
    if kind == "check":
        return (
            "Trước nước chiếu, em nhìn các đường tấn công: "
            "quân nào đang **nhắm** tới vua đối phương?"
        )
    if kind == "capture":
        return (
            f"Trước nước `{moment.ply.san}`, em thấy quân nào "
            "đang **bị đe dọa** hoặc có thể bị bắt?"
        )
    if kind == "eval_drop":
        return (
            f"Trước nước `{moment.ply.san}`, em thấy **điểm yếu** nào "
            "(quân treo, vua hở, ô yếu)?"
        )
    return "Em chỉ ra quân nào trên bàn đang **bị đe dọa** rõ nhất?"


def _primary_apply(kind: str, moment: TeachingMoment) -> str:
    if kind in {"check", "mate"}:
        return (
            "Em tìm **một** nước chiếu (hoặc nước buộc vua phải phản ứng). "
            "Chưa cần nước hay nhất — hãy nói nước em chọn và vì sao."
        )
    if kind == "hanging":
        return (
            "Em thử tìm cách **cứu** quân đang treo: chạy, che, hoặc bắt đổi. "
            "Em chọn cách nào trước?"
        )
    if kind == "capture":
        return (
            f"Ở thế trước `{moment.ply.san}`, em có nước **bắt quân an toàn** nào không? "
            "Em mô tả ô đến (không cần ký hiệu chuyên sâu)."
        )
    if kind == "eval_drop":
        return (
            f"Thay vì `{moment.ply.san}`, em thử nghĩ **một** nước khác an toàn hơn. "
            "Em mô tả ý tưởng (không cần điểm số máy)."
        )
    return "Em tìm một nước **chiếu** hoặc **bắt quân** phù hợp với vị trí này."


def _primary_analyze(kind: str, moment: TeachingMoment) -> str:
    if kind == "hanging":
        return (
            "Vì sao quân lại trở thành **quân treo** sau nước vừa rồi? "
            "Em sẽ nhìn **bạn bảo vệ** trước hay sau khi đi?"
        )
    if kind in {"check", "mate"}:
        return (
            "Sau ý tưởng chiếu này, cấu trúc vua hai bên thay đổi thế nào? "
            "Cánh nào **chắc** hơn, cánh nào **hở** hơn?"
        )
    if kind == "eval_drop":
        return (
            "Vì sao nước đó làm thế cờ **kém hơn** cho bên đi? "
            "Em nói về an toàn vua hoặc quân bị bỏ rơi — không cần số eval."
        )
    return (
        f"Nếu không đi `{moment.ply.san}` mà đổi hướng, "
        "vua em có an toàn hơn không? Em giải thích ngắn."
    )
