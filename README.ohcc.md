# OpenHarness Chess Coaching (OHCC)

Domain layer on top of **OpenHarness** for **CLB Cờ vua Dương Sinh**.

## License commitment

- Project: **MIT**
- Engine: **Arasan (MIT)** only — never Stockfish (GPL)
- Analysis style: custom heuristics — never Maia (GPL)
- Chess parsing: `ohcc/chess_core` — never `python-chess` (GPL-3)

See `THIRD_PARTY.md` and `docs/ohcc/license-compliance.md`.

## Layout (Step 1 scaffold)

```text
ohcc/                     Domain Python package
plugins/ohcc-coach/       OpenHarness plugin (agents, skills, mcp.json)
mcp-servers/arasan-mcp/   UCI → MCP (Step 4)
mcp-servers/vision-board-mcp/
vendor/arasan/            Engine license + bin/ (gitignored binaries)
vault/                    Obsidian curriculum vault
admin-portal/             Next.js admin (stub)
docs/ohcc/                Architecture & pedagogy docs
```

## Pedagogy

- Persona: **Thầy Tường** (`ohcc/coach/personas/thay_tuong.md` — full prompt in Step 2)
- Method: **Socratic** + **Bloom scaffolding** (remember / apply / analyze)
- Memory: `vault/01-students/` + `ohcc/coach/memory/`

## Load the plugin

`plugins/ohcc-coach` is the committed source. OpenHarness loads project plugins from
`.openharness/plugins/` — see `plugins/ohcc-coach/README.md`.

## Roadmap steps

1. Directory structure — done
2. System prompt Thầy Tường — done
3. `ScaffoldingPuzzleBuilder` pipeline — done
4. `arasan-mcp` UCI implementation — done
5. `vision-board-mcp` + board-photo skill — done
6. Admin portal (Next.js + Tailwind) — done

### Scaffolding quick start

```bash
python -m ohcc.scaffolding --pgn data/sample-pgn/scholars_mate.pgn --vault vault --level primary
# With Arasan eval drops (requires binary + ARASAN_PATH):
python -m ohcc.scaffolding --pgn data/sample-pgn/italian_capture.pgn --vault vault --arasan
```

Puzzles land in `vault/03-puzzles/bloom-{remember,apply,analyze}/`.

### arasan-mcp

```bash
# Place MIT Arasan binary, then:
set ARASAN_PATH=vendor/arasan/bin/arasan.exe   # Windows example
python -m arasan_mcp
```

Tools: `analyze_fen`, `evaluate_position`, `compare_positions` (coach-internal scores only).

### vision-board-mcp

```bash
set PYTHONPATH=mcp-servers/vision-board-mcp/src
set OHCC_VAULT=vault
python -m vision_board_mcp
```

Tools: `analyze_board_image_tool` (optional `fen_hint`), `validate_fen_tool`, `list_inbox_reviews`.

### Admin portal (Next.js)

```bash
cd admin-portal
npm install
set OHCC_VAULT=..\vault
npm run dev
```

http://localhost:3100 — students, lessons, puzzles, games, inbox.

See `scripts/ohcc/dev_stack.md` for the full local stack.

### One-shot local demo

```bash
# From repo root (creates puzzles + inbox notes from sample PGNs)
python scripts/ohcc/run_local_demo.py

# Multi-provider LLM coach (Antigravity / Claude / Grok / Codex CLIs)
python scripts/ohcc/run_llm_coach_demo.py
# → vault/_meta/llm-reviews/  then open http://localhost:3100/llm

# Admin UI
cd admin-portal
set OHCC_VAULT=..\vault
npm run dev
# http://localhost:3100
```

| Admin route | Nội dung |
|-------------|----------|
| `/analysis` | Pipeline cờ heuristic (không LLM) |
| `/llm` | **Live:** dán PGN + chọn 1 model → xem pipeline + kết quả coach |

### Live analyze (UI)

1. Mở http://localhost:3100/llm  
2. Dán PGN (hoặc “Dùng PGN mẫu”)  
3. Chọn **một** trong Antigravity / Claude / Grok / Codex  
4. Bấm **Chạy phân tích** — timeline 8 bước + replay + Bloom + phản hồi LLM  

API: `POST /api/live-analyze` `{ "pgn": "...", "provider": "claude", "timeout": 180 }`
