---
name: board-photo-intake
description: Ingest a chessboard photo (Zalo/Telegram), resolve FEN via vision-board-mcp, and prepare Socratic review.
---

# Board photo intake

Use **vision-board-mcp** tools:

1. `analyze_board_image_tool` with image path; add `fen_hint` when teacher provides FEN.
2. `validate_fen_tool` on the result.
3. `list_inbox_reviews` if waiting on pending photos.

## After FEN is confirmed

- Switch to `socratic-game-analysis` as **Thầy Tường**.
- Do **not** dump raw engine eval to young students.
- Optionally `scaffolding-puzzle-builder` if building homework from a related PGN.

## Rules

- MIT only — no Stockfish/Maia.
- Prefer teacher `fen_hint` over guessing.
- Pending photos live in `vault/00-inbox/`.
