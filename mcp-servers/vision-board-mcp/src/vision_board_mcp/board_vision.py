"""Board photo → FEN helpers (MIT).

Default path is deterministic and license-safe:
- validate image file
- accept optional fen_hint from teacher / OCR pipeline
- optional lightweight grid metadata (no GPL models)

Heavy neural board-recognition models are intentionally pluggable and off by default
so OHCC never pulls GPL or unvetted weights.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

# Minimal FEN placement sanity (8 ranks).
_FEN_PLACEMENT = re.compile(
    r"^([rnbqkpRNBQKP1-8]+/){7}[rnbqkpRNBQKP1-8]+$"
)


@dataclass
class VisionResult:
    """Structured result for coach / vault inbox."""

    ok: bool
    image_path: str
    fen: str | None = None
    confidence: float = 0.0
    source: str = "none"  # fen_hint | pending_review | error
    message: str = ""
    side_to_move: str | None = None
    inbox_note: str | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def is_image_path(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def validate_fen(fen: str) -> tuple[bool, str]:
    """Basic FEN validation without python-chess."""
    parts = fen.strip().split()
    if len(parts) < 1:
        return False, "Empty FEN"
    placement = parts[0]
    if not _FEN_PLACEMENT.match(placement):
        return False, "Invalid FEN placement ranks"
    # Count squares per rank
    for rank in placement.split("/"):
        n = 0
        for ch in rank:
            if ch.isdigit():
                n += int(ch)
            elif ch in "rnbqkpRNBQKP":
                n += 1
            else:
                return False, f"Invalid piece char {ch!r}"
        if n != 8:
            return False, f"Rank does not sum to 8: {rank!r}"
    stm = parts[1] if len(parts) > 1 else "w"
    if stm not in {"w", "b"}:
        return False, "side to move must be w or b"
    return True, "ok"


def analyze_board_image(
    image_path: Path | str,
    *,
    fen_hint: str | None = None,
    vault_inbox: Path | str | None = None,
    side_hint: str | None = None,
) -> VisionResult:
    """Analyze a board photo into a FEN suggestion.

    Without an external vision backend, *fen_hint* is required for a confirmed FEN.
    Images are still recorded to the vault inbox for teacher review.
    """
    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        return VisionResult(
            ok=False,
            image_path=str(path),
            source="error",
            message=f"Image not found: {path}",
        )
    if not is_image_path(path):
        return VisionResult(
            ok=False,
            image_path=str(path),
            source="error",
            message=f"Unsupported image type: {path.suffix}",
        )

    warnings: list[str] = []
    fen: str | None = None
    confidence = 0.0
    source = "pending_review"
    message = (
        "Ảnh đã nhận. Chưa có backend nhận diện quân tự động (MIT-safe). "
        "Cung cấp fen_hint hoặc chỉnh FEN trong vault inbox."
    )

    if fen_hint:
        ok, why = validate_fen(fen_hint)
        if ok:
            fen = _normalize_fen(fen_hint, side_hint=side_hint)
            confidence = 0.95
            source = "fen_hint"
            message = "FEN from teacher/OCR hint (validated)."
        else:
            warnings.append(f"fen_hint invalid: {why}")
            message = f"fen_hint rejected ({why}); saved for manual review."

    inbox_note = None
    if vault_inbox is not None:
        inbox_note = str(
            write_inbox_note(
                Path(vault_inbox),
                image_path=path,
                fen=fen,
                source=source,
                message=message,
                warnings=warnings,
            )
        )

    return VisionResult(
        ok=fen is not None,
        image_path=str(path),
        fen=fen,
        confidence=confidence,
        source=source,
        message=message,
        side_to_move=fen.split()[1] if fen else side_hint,
        inbox_note=inbox_note,
        warnings=warnings,
    )


def write_inbox_note(
    inbox_dir: Path,
    *,
    image_path: Path,
    fen: str | None,
    source: str,
    message: str,
    warnings: list[str],
) -> Path:
    """Write an Obsidian note under vault/00-inbox for board photo review."""
    inbox_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    note_path = inbox_dir / f"board-photo-{ts}-{image_path.stem}.md"
    fen_line = fen or ""
    warn_block = "\n".join(f"- {w}" for w in warnings) if warnings else "- (none)"
    body = f"""---
type: board-photo-review
image: "{image_path.as_posix()}"
fen: "{fen_line}"
source: {source}
tags: [ohcc, vision, inbox]
created: {ts}
---

# Board photo review — {image_path.name}

## Status

{message}

## FEN

```
{fen_line or "(pending teacher)"}
```

## Warnings

{warn_block}

## Next steps (Thầy Tường)

1. Xác nhận FEN với phụ huynh/GV nếu cần.
2. Chạy phân tích Socratic / scaffolding với FEN đã chốt.
3. Không dump eval thô cho học viên nhỏ.
"""
    note_path.write_text(body, encoding="utf-8")
    # Sidecar JSON for admin portal
    meta_path = note_path.with_suffix(".json")
    meta_path.write_text(
        json.dumps(
            {
                "image": str(image_path),
                "fen": fen,
                "source": source,
                "message": message,
                "warnings": warnings,
                "created": ts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return note_path


def _normalize_fen(fen: str, *, side_hint: str | None = None) -> str:
    parts = fen.strip().split()
    placement = parts[0]
    stm = side_hint if side_hint in {"w", "b"} else (parts[1] if len(parts) > 1 else "w")
    castling = parts[2] if len(parts) > 2 else "-"
    ep = parts[3] if len(parts) > 3 else "-"
    half = parts[4] if len(parts) > 4 else "0"
    full = parts[5] if len(parts) > 5 else "1"
    return f"{placement} {stm} {castling} {ep} {half} {full}"
