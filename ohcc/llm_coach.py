"""Run Thầy Tường game analysis via OpenHarness CLI providers.

Providers: antigravity (agy), claude, grok, codex — subscription CLIs, not API keys.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from openharness.api.antigravity_cli_engine import antigravity_cli_status, find_antigravity_cli
from openharness.api.claude_cli_detect import claude_auth_status, find_claude_cli
from openharness.api.codex_cli_engine import codex_cli_status, find_codex_cli
from openharness.api.grok_cli_engine import find_grok_cli, grok_cli_status


PROVIDERS = ("antigravity", "claude", "grok", "codex")


@dataclass
class ProviderStatus:
    id: str
    label: str
    binary: str | None
    ready: bool
    detail: str


@dataclass
class LlmReview:
    provider: str
    label: str
    status: str  # ok | error | skipped
    binary: str | None = None
    duration_ms: int = 0
    model_note: str = ""
    prompt_excerpt: str = ""
    response: str = ""
    error: str = ""
    game_file: str = ""
    fen: str = ""
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return asdict(self)


def probe_providers() -> list[ProviderStatus]:
    out: list[ProviderStatus] = []

    ready, detail, path = antigravity_cli_status()
    out.append(
        ProviderStatus(
            "antigravity",
            "Antigravity (agy / Google)",
            path or find_antigravity_cli(),
            ready,
            detail,
        )
    )

    st = claude_auth_status()
    claude_path = st.cli_path or find_claude_cli()
    out.append(
        ProviderStatus(
            "claude",
            "Claude Code CLI",
            claude_path,
            bool(st.ready),
            st.detail or st.auth_method or "claude",
        )
    )

    ready, detail, path = grok_cli_status()
    out.append(
        ProviderStatus(
            "grok",
            "Grok Build CLI (xAI)",
            path or find_grok_cli(),
            ready,
            detail,
        )
    )

    ready, detail, path = codex_cli_status()
    out.append(
        ProviderStatus(
            "codex",
            "Codex CLI (OpenAI)",
            path or find_codex_cli(),
            ready,
            detail,
        )
    )
    return out


def build_coach_prompt(*, game_title: str, pgn: str, fen: str, san_moment: str) -> str:
    """Short prompt — keep under Windows argv limits for -p CLIs."""
    return f"""Bạn là Thầy Tường (CLB Cờ vua Dương Sinh). Phân tích ngắn vị trí cờ cho phụ huynh/GV.

Ván: {game_title}
Khoảnh khắc (SAN): {san_moment}
FEN: {fen}

PGN:
{pgn[:800]}

Yêu cầu (Socratic + Bloom):
1) Nêu 1 khoảnh khắc dạy (không dump eval thô / không nói "máy bảo +2").
2) Viết 3 câu hỏi gợi mở: Nhận biết / Áp dụng / Phân tích (mỗi tầng 1 câu).
3) 1 gợi ý cho phụ huynh luyện 5 phút ở nhà.
4) Ký tên cuối: — Thầy Tường via LLM

Trả lời tiếng Việt, tối đa ~250 từ. Không viết code."""


def _run_cmd(cmd: list[str], *, timeout: int, cwd: Path, stdin_text: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(cwd),
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def run_provider_analysis(
    provider: str,
    prompt: str,
    *,
    cwd: Path,
    timeout: int = 120,
) -> LlmReview:
    """Invoke one CLI provider with a coach prompt."""
    labels = {
        "antigravity": "Antigravity (agy)",
        "claude": "Claude Code",
        "grok": "Grok Build",
        "codex": "Codex CLI",
    }
    label = labels.get(provider, provider)
    prompt_excerpt = prompt[:240].replace("\n", " ")

    if provider == "antigravity":
        cli = find_antigravity_cli()
        if not cli:
            return LlmReview(provider, label, "skipped", error="agy not found", prompt_excerpt=prompt_excerpt)
        # agy: -p/--print takes the prompt; put flags before the prompt string.
        cmd = [
            cli,
            "--dangerously-skip-permissions",
            "--output-format",
            "text",
            "--print-timeout",
            "3m",
            "-p",
            prompt,
        ]
        return _execute(provider, label, cli, cmd, cwd, timeout, prompt_excerpt)

    if provider == "claude":
        cli = find_claude_cli()
        if not cli:
            return LlmReview(provider, label, "skipped", error="claude not found", prompt_excerpt=prompt_excerpt)
        cmd = [
            cli,
            "-p",
            prompt,
            "--output-format",
            "text",
            "--dangerously-skip-permissions",
        ]
        return _execute(provider, label, cli, cmd, cwd, timeout, prompt_excerpt, stdin_null=True)

    if provider == "grok":
        cli = find_grok_cli()
        if not cli:
            return LlmReview(provider, label, "skipped", error="grok not found", prompt_excerpt=prompt_excerpt)
        cmd = [cli, "-p", prompt, "--always-approve"]
        return _execute(provider, label, cli, cmd, cwd, timeout, prompt_excerpt)

    if provider == "codex":
        cli = find_codex_cli()
        if not cli:
            return LlmReview(provider, label, "skipped", error="codex not found", prompt_excerpt=prompt_excerpt)
        cmd = [
            cli,
            "--dangerously-bypass-approvals-and-sandbox",
            "exec",
            "--skip-git-repo-check",
            "-",
        ]
        return _execute(
            provider, label, cli, cmd, cwd, timeout, prompt_excerpt, stdin_text=prompt
        )

    return LlmReview(provider, label, "error", error=f"unknown provider {provider}")


def _execute(
    provider: str,
    label: str,
    cli: str,
    cmd: list[str],
    cwd: Path,
    timeout: int,
    prompt_excerpt: str,
    *,
    stdin_text: str | None = None,
    stdin_null: bool = False,
) -> LlmReview:
    t0 = time.perf_counter()
    try:
        if stdin_null:
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=str(cwd),
            )
            code, out, err = proc.returncode, proc.stdout or "", proc.stderr or ""
        else:
            code, out, err = _run_cmd(cmd, timeout=timeout, cwd=cwd, stdin_text=stdin_text)
        ms = int((time.perf_counter() - t0) * 1000)
        text = out.strip()
        if not text and err.strip():
            # some CLIs put useful text on stderr
            text = err.strip()
        if code != 0 and not text:
            return LlmReview(
                provider,
                label,
                "error",
                binary=cli,
                duration_ms=ms,
                prompt_excerpt=prompt_excerpt,
                error=f"exit {code}: {err[:500]}",
            )
        # strip obvious hook noise
        cleaned = _clean_output(text)
        return LlmReview(
            provider,
            label,
            "ok",
            binary=cli,
            duration_ms=ms,
            model_note=f"CLI: {Path(cli).name}",
            prompt_excerpt=prompt_excerpt,
            response=cleaned,
        )
    except subprocess.TimeoutExpired:
        ms = int((time.perf_counter() - t0) * 1000)
        return LlmReview(
            provider,
            label,
            "error",
            binary=cli,
            duration_ms=ms,
            prompt_excerpt=prompt_excerpt,
            error=f"timeout after {timeout}s",
        )
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        return LlmReview(
            provider,
            label,
            "error",
            binary=cli,
            duration_ms=ms,
            prompt_excerpt=prompt_excerpt,
            error=str(exc),
        )


def _clean_output(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if "hook-handler.js" in line or "SessionEnd hook" in line:
            continue
        if line.strip().startswith("node:internal"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def analyze_game_with_llms(
    *,
    game_path: Path,
    fen: str,
    san_moment: str,
    providers: list[str] | None = None,
    cwd: Path | None = None,
    timeout: int = 120,
    out_dir: Path | None = None,
) -> list[LlmReview]:
    pgn = game_path.read_text(encoding="utf-8")
    title = game_path.stem
    for line in pgn.splitlines():
        if line.startswith('[Event "'):
            title = line.split('"', 2)[1]
            break
    prompt = build_coach_prompt(
        game_title=title, pgn=pgn, fen=fen, san_moment=san_moment
    )
    work = cwd or game_path.parent
    wanted = providers or list(PROVIDERS)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    reviews: list[LlmReview] = []
    with ThreadPoolExecutor(max_workers=max(1, len(wanted))) as pool:
        futs = {
            pool.submit(run_provider_analysis, pid, prompt, cwd=work, timeout=timeout): pid
            for pid in wanted
        }
        for fut in as_completed(futs):
            review = fut.result()
            review.game_file = game_path.name
            review.fen = fen
            reviews.append(review)
    # stable order: antigravity, claude, grok, codex
    order = {p: i for i, p in enumerate(PROVIDERS)}
    reviews.sort(key=lambda r: order.get(r.provider, 99))

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {
            "game": game_path.name,
            "fen": fen,
            "san_moment": san_moment,
            "created": stamp,
            "providers_probed": [asdict(p) for p in probe_providers()],
            "reviews": [r.as_dict() for r in reviews],
        }
        path = out_dir / f"{game_path.stem}-llm-{stamp}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # also latest pointer
        (out_dir / f"{game_path.stem}-llm-latest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return reviews
