# OHCC directory structure

Canonical layout after Step 1 scaffold. See also `README.ohcc.md`.

## Domain isolation

| Layer | Location |
|-------|----------|
| OpenHarness core | `src/openharness/`, `ohmo/` (unchanged) |
| Domain logic | `ohcc/` |
| Agent plugin | `plugins/ohcc-coach/` |
| MCP servers | `mcp-servers/*` |
| Engine vendor | `vendor/arasan/` |
| Curriculum vault | `vault/` |
| Admin UI | `admin-portal/` |

## Why not put chess code inside `src/openharness/`

OpenHarness is reusable agent infrastructure. Chess coaching is a product domain
and stays out of the core package for license clarity and upstream hygiene.
