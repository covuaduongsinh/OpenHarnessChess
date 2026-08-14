# OHCC Admin Portal

Next.js + Tailwind admin UI for **CLB Cờ vua Dương Sinh**.

Reads the Obsidian **vault** on disk (no GPL engines in the browser).

## Routes

| Path | Source |
|------|--------|
| `/` | Dashboard counts |
| `/analysis` | **Game analysis model UI** — moments + Bloom Socratic + mini board |
| `/students` | `vault/01-students` |
| `/lessons` | `vault/02-lessons` |
| `/puzzles` | `vault/03-puzzles/bloom-*` |
| `/games` | `vault/04-games` + linked analysis cards |
| `/inbox` | `vault/00-inbox` (board photos) |

## Dev

```bash
cd admin-portal
npm install
# optional: set OHCC_VAULT to absolute vault path
set OHCC_VAULT=D:\code\OpenHarnessChess\vault
npm run dev
```

Open http://localhost:3100

## License

MIT — same commercial constraints as OHCC (no Stockfish/Maia in the stack).
