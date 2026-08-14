# ohcc-coach plugin

OpenHarness plugin for **OpenHarness Chess Coaching (OHCC)**.

## Load path

OpenHarness discovers project plugins under `.openharness/plugins/` (gitignored).  
This directory is the **version-controlled source of truth**.

Install / link for local runs:

```bash
# Option A: copy or junction into project plugins dir
# Windows (pwsh):
New-Item -ItemType Junction -Path .openharness/plugins/ohcc-coach -Target (Resolve-Path plugins/ohcc-coach)

# Then enable in settings:
# allow_project_plugins = true
```

Or install into the user plugins directory via OpenHarness plugin installer.

## Contents

| Path | Role |
|------|------|
| `agents/coach-agent.md` | CoachAgent (Thầy Tường) |
| `skills/` | Scaffolding, Socratic analysis, student memory |
| `commands/` | Slash commands |
| `mcp.json` | arasan-mcp + vision-board-mcp |

## License

MIT — no Stockfish / Maia / GPL dependencies.
