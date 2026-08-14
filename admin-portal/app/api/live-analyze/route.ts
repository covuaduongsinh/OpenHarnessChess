import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

const PROVIDERS = new Set(["antigravity", "claude", "grok", "codex"]);

function repoRoot(): string {
  // admin-portal is one level under monorepo root
  return path.resolve(process.cwd(), "..");
}

function findPython(): string {
  const root = repoRoot();
  const candidates = [
    path.join(root, ".venv", "Scripts", "python.exe"),
    path.join(root, ".venv", "bin", "python"),
    path.join(root, ".openharness-venv", "Scripts", "python.exe"),
    "python",
  ];
  for (const c of candidates) {
    if (c === "python" || fs.existsSync(c)) return c;
  }
  return "python";
}

function runPython(args: string[], stdinText: string, timeoutMs: number): Promise<{
  code: number | null;
  stdout: string;
  stderr: string;
}> {
  const python = findPython();
  const root = repoRoot();
  return new Promise((resolve) => {
    const child = spawn(python, args, {
      cwd: root,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        PYTHONPATH: [
          path.join(root, "src"),
          root,
          process.env.PYTHONPATH || "",
        ].join(path.delimiter),
      },
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      resolve({ code: 124, stdout, stderr: stderr + "\n[timeout]" });
    }, timeoutMs);

    child.stdout.on("data", (d) => {
      stdout += d.toString("utf8");
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString("utf8");
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ code: 1, stdout, stderr: String(err) });
    });
    if (stdinText) {
      child.stdin.write(stdinText, "utf8");
    }
    child.stdin.end();
  });
}

export async function GET() {
  const root = repoRoot();
  const script = path.join(root, "scripts", "ohcc", "analyze_pgn_live.py");
  const rootEscaped = root.replace(/\\/g, "\\\\");
  const probeCode = [
    "import json,sys",
    "from pathlib import Path",
    `root=Path(r'''${rootEscaped}''')`,
    "sys.path.insert(0, str(root/'src'))",
    "sys.path.insert(0, str(root))",
    "from ohcc.llm_coach import probe_providers",
    "print(json.dumps([{'id':p.id,'label':p.label,'ready':p.ready,'binary':p.binary,'detail':p.detail} for p in probe_providers()], ensure_ascii=False))",
  ].join(";");
  const { stdout, stderr, code } = await runPython(["-c", probeCode], "", 30_000);
  try {
    const providers = JSON.parse(stdout.trim().split(/\r?\n/).filter(Boolean).pop() || "[]");
    return NextResponse.json({ ok: true, providers, python: findPython(), script });
  } catch {
    return NextResponse.json(
      { ok: false, error: "probe failed", stdout, stderr, code },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.pgn !== "string") {
    return NextResponse.json({ ok: false, error: "Missing pgn" }, { status: 400 });
  }
  const provider = String(body.provider || "").toLowerCase();
  if (!PROVIDERS.has(provider)) {
    return NextResponse.json(
      { ok: false, error: "provider must be antigravity|claude|grok|codex" },
      { status: 400 }
    );
  }
  const pgn = body.pgn.trim();
  if (pgn.length < 10) {
    return NextResponse.json({ ok: false, error: "PGN too short" }, { status: 400 });
  }
  if (pgn.length > 80_000) {
    return NextResponse.json({ ok: false, error: "PGN too large" }, { status: 400 });
  }
  const timeoutSec = Math.min(Math.max(Number(body.timeout) || 180, 30), 300);
  const root = repoRoot();
  const script = path.join(root, "scripts", "ohcc", "analyze_pgn_live.py");
  if (!fs.existsSync(script)) {
    return NextResponse.json({ ok: false, error: `Script missing: ${script}` }, { status: 500 });
  }

  // Write temp PGN to avoid Windows argv length issues
  const tmpDir = path.join(root, "vault", "_meta", "llm-reviews", "live");
  fs.mkdirSync(tmpDir, { recursive: true });
  const tmpPgn = path.join(tmpDir, `input-${Date.now()}.pgn`);
  fs.writeFileSync(tmpPgn, pgn, "utf8");

  const { stdout, stderr, code } = await runPython(
    [
      script,
      "--provider",
      provider,
      "--pgn-file",
      tmpPgn,
      "--timeout",
      String(timeoutSec),
      "--max-moments",
      String(body.maxMoments || 4),
    ],
    "",
    (timeoutSec + 30) * 1000
  );

  // cleanup temp input (keep result json from script)
  try {
    fs.unlinkSync(tmpPgn);
  } catch {
    /* ignore */
  }

  const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
  const last = lines[lines.length - 1] || "";
  try {
    const data = JSON.parse(last);
    return NextResponse.json({
      ...data,
      _meta: { exitCode: code, stderrTail: stderr.slice(-800) },
    });
  } catch {
    return NextResponse.json(
      {
        ok: false,
        error: "Failed to parse analyzer output",
        exitCode: code,
        stdoutTail: stdout.slice(-2000),
        stderrTail: stderr.slice(-2000),
      },
      { status: 500 }
    );
  }
}
