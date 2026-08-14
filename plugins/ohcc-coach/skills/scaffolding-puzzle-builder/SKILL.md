---
name: scaffolding-puzzle-builder
description: Build Bloom-scaffolded chess puzzles from PGN and export Obsidian Markdown into the vault.
---

# Scaffolding Puzzle Builder

Implementation: `ohcc.scaffolding.puzzle_builder.ScaffoldingPuzzleBuilder` (MIT, no Stockfish/Maia/python-chess).

## Workflow

1. Read PGN (`vault/04-games/`, `data/sample-pgn/`, or user path).
2. Replay moves with `ohcc.chess_core` (SAN → FEN).
3. Detect teaching moments: check / mate / capture / hanging, plus optional **Arasan eval drops** (`--arasan`).
4. For each moment, generate **3 Bloom layers**: remember → apply → analyze (Socratic, Thầy Tường voice).
5. Write Markdown into `vault/03-puzzles/bloom-*/`.

## CLI

```bash
python -m ohcc.scaffolding --pgn data/sample-pgn/scholars_mate.pgn --vault vault --level primary
python -m ohcc.scaffolding --pgn data/sample-pgn/italian_capture.pgn --vault vault --arasan
```

## Python

```python
from pathlib import Path
from ohcc.scaffolding import ScaffoldingPuzzleBuilder

builder = ScaffoldingPuzzleBuilder(vault_root=Path("vault"), student_level="primary")
result = builder.build(pgn_path=Path("data/sample-pgn/scholars_mate.pgn"))
print(result.written)
```

## Output contract

Each note has YAML frontmatter:

- `type: scaffolding-puzzle`
- `bloom`, `fen`, `source_pgn`, `student_level`
- optional: `moment_kind`, `ply_index`, `san`, `severity`

Student section = **one Socratic question** (no solution move, no raw eval).  
Teacher note is separate and must not be read verbatim to children.

## Rules

- No GPL engines or libraries.
- Prefer Arasan (MIT) for severity when available; heuristics still work offline.
- Follow Thầy Tường persona (`ohcc/coach/personas/thay_tuong.md`).
