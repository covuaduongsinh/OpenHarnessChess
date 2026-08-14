# Arasan engine vendor notice

## License

**Arasan** is distributed under the **MIT License**.

Official project: https://github.com/jdart1/arasan-chess  
(Do not substitute Stockfish or other GPL engines.)

## Binary policy

- Binaries under `vendor/arasan/bin/` are **not committed** (see `.gitignore`).
- Keep a copy of Arasan's MIT `LICENSE` next to this file when vendoring.
- Verify the license file on every download via `scripts/ohcc/download_arasan.py` (Step 4+).

## Why Arasan

OHCC requires a commercializable MIT stack:

| Engine / lib | License | OHCC status |
|--------------|---------|-------------|
| Arasan | MIT | **Required** |
| Stockfish | GPL | **Forbidden** |
| Maia | GPL | **Forbidden** |
| python-chess | GPL-3 | **Forbidden** |

## Obtain binary

1. Build from the Arasan upstream source, or download a release binary if available.
2. Place the executable at:
   - Windows: `vendor/arasan/bin/arasan.exe`
   - Unix: `vendor/arasan/bin/arasan`
3. Set `ARASAN_PATH` to that path for `arasan-mcp`.
