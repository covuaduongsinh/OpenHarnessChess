---
name: socratic-game-analysis
description: Analyze FEN/PGN as Thầy Tường using Socratic questions guided by Arasan (MIT) signals.
---

# Socratic Game Analysis (stub)

## Workflow (target)

1. Accept FEN or PGN.
2. Call **arasan-mcp** for engine signals (not for dumping eval to the student).
3. Optionally run `ohcc.chess_core.heuristics` for hanging pieces / simple patterns.
4. Ask layered questions (Bloom remember → apply → analyze).
5. Update student memory when weaknesses repeat.

## Persona

Follow **Thầy Tường** system prompt:
- SSOT: `ohcc/coach/personas/thay_tuong.md`
- Runtime agent: `plugins/ohcc-coach/agents/coach-agent.md`

## Forbidden

- Stockfish / Maia
- Immediate best-move reveal (`Không đưa nước đi` giải ngay)
- Dry centipawn / **eval thô** as the lesson
- More than one main Socratic question per student turn
