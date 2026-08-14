# License compliance checklist (OHCC)

## Hard bans

- [ ] No Stockfish binary, source, or API dependency
- [ ] No Maia model or GPL neural nets for coaching
- [ ] No `python-chess` import or dependency
- [ ] No GPL/AGPL/LGPL runtime requirements for OHCC features

## Required

- [ ] Root `LICENSE` remains MIT
- [ ] `THIRD_PARTY.md` updated for new deps
- [ ] Arasan binary accompanied by MIT license text in `vendor/arasan/`
- [ ] MCP servers declare `license = "MIT"` in their `pyproject.toml`

## Pre-release audit

```text
1. Scan deps for GPL keywords
2. Confirm ARASAN_PATH points to Arasan, not Stockfish
3. Confirm scaffolding does not shell out to banned engines
```

Script placeholder: `scripts/ohcc/license_audit.py`
