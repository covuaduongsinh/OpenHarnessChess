# OHCC local dev stack

## 1. Scaffolding puzzles

```bash
python -m ohcc.scaffolding --pgn data/sample-pgn/scholars_mate.pgn --vault vault
python -m ohcc.scaffolding --pgn data/sample-pgn/italian_capture.pgn --vault vault --arasan
```

## 2. arasan-mcp

```bash
set ARASAN_PATH=vendor\arasan\bin\arasan.exe
set PYTHONPATH=mcp-servers\arasan-mcp\src
python -m arasan_mcp
```

## 3. vision-board-mcp

```bash
set PYTHONPATH=mcp-servers\vision-board-mcp\src
set OHCC_VAULT=vault
python -m vision_board_mcp
```

## 4. Admin portal

```bash
cd admin-portal
npm install
set OHCC_VAULT=..\vault
npm run dev
```

Open http://localhost:3100

## 5. Plugin

Link `plugins/ohcc-coach` into `.openharness/plugins/` and set `allow_project_plugins=true`.
