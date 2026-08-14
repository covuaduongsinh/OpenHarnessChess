# vision-board-mcp

MCP server for **photos of physical chessboards** (Zalo / Telegram intake).

## License

MIT. No GPL vision models or engines. Auto piece-recognition backends are pluggable and off by default.

## Tools

| Tool | Purpose |
|------|---------|
| `analyze_board_image_tool` | Image path + optional `fen_hint` → FEN + vault inbox note |
| `validate_fen_tool` | Validate FEN without python-chess |
| `list_inbox_reviews` | List pending board-photo notes |

## Workflow

1. Parent/teacher sends board photo via channel (Zalo/Telegram → gateway later).
2. Call `analyze_board_image_tool` with path; pass `fen_hint` when known.
3. Review note lands in `vault/00-inbox/`.
4. CoachAgent (Thầy Tường) runs Socratic analysis on confirmed FEN.

## Run

```bash
set PYTHONPATH=mcp-servers/vision-board-mcp/src
set OHCC_VAULT=vault
python -m vision_board_mcp
```
