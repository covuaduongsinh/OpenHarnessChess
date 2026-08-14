"""Provider/auth capability helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from openharness.auth.external import describe_external_binding
from openharness.auth.storage import load_external_binding
from openharness.api.registry import detect_provider_from_registry
from openharness.config.settings import Settings

_AUTH_KIND: dict[str, str] = {
    "anthropic": "api_key",
    "openai_compat": "api_key",
    "copilot": "oauth_device",
    "openai_codex": "external_oauth",
    "anthropic_claude": "external_oauth",
}

_VOICE_REASON: dict[str, str] = {
    "anthropic": (
        "voice mode shell exists, but live voice auth/streaming is not configured in this build"
    ),
    "openai_compat": "voice mode is not wired for OpenAI-compatible providers in this build",
    "copilot": "voice mode is not supported for GitHub Copilot",
    "openai_codex": "voice mode is not supported for Codex subscription auth",
    "anthropic_claude": "voice mode is not supported for Claude subscription auth",
}


@dataclass(frozen=True)
class ProviderInfo:
    """Resolved provider metadata for UI and diagnostics."""

    name: str
    auth_kind: str
    voice_supported: bool
    voice_reason: str


def detect_provider(settings: Settings) -> ProviderInfo:
    """Infer the active provider and rough capability set using the registry."""
    if settings.provider == "openai_codex":
        return ProviderInfo(
            name="openai-codex",
            auth_kind="codex_cli",
            voice_supported=False,
            voice_reason=_VOICE_REASON["openai_codex"],
        )
    if settings.provider == "anthropic_claude":
        return ProviderInfo(
            name="claude-subscription",
            auth_kind="claude_code_cli",
            voice_supported=False,
            voice_reason=_VOICE_REASON["anthropic_claude"],
        )
    if settings.provider in {"grok", "grok_cli", "xai_grok"}:
        return ProviderInfo(
            name="grok-cli",
            auth_kind="grok_cli",
            voice_supported=False,
            voice_reason="voice mode is not wired for Grok Build CLI",
        )
    if settings.provider in {"antigravity", "google_antigravity", "agy"}:
        return ProviderInfo(
            name="antigravity-cli",
            auth_kind="antigravity_cli",
            voice_supported=False,
            voice_reason="voice mode is not wired for Antigravity CLI",
        )
    if settings.api_format == "copilot":
        return ProviderInfo(
            name="github_copilot",
            auth_kind="oauth_device",
            voice_supported=False,
            voice_reason=_VOICE_REASON["copilot"],
        )

    spec = detect_provider_from_registry(
        model=settings.model,
        api_key=settings.api_key or None,
        base_url=settings.base_url,
    )

    if spec is not None:
        backend = spec.backend_type
        return ProviderInfo(
            name=spec.name,
            auth_kind=_AUTH_KIND.get(backend, "api_key"),
            voice_supported=False,
            voice_reason=_VOICE_REASON.get(backend, "voice mode is not supported for this provider"),
        )

    # Fallback: use api_format to pick a sensible default
    if settings.api_format == "openai":
        return ProviderInfo(
            name="openai-compatible",
            auth_kind="api_key",
            voice_supported=False,
            voice_reason=_VOICE_REASON["openai_compat"],
        )
    return ProviderInfo(
        name="anthropic",
        auth_kind="api_key",
        voice_supported=False,
        voice_reason=_VOICE_REASON["anthropic"],
    )


def auth_status(settings: Settings) -> str:
    """Return a compact auth status string."""
    if settings.api_format == "copilot":
        from openharness.api.copilot_auth import load_copilot_auth

        auth_info = load_copilot_auth()
        if not auth_info:
            return "missing (run 'oh auth copilot-login')"
        if auth_info.enterprise_url:
            return f"configured (enterprise: {auth_info.enterprise_url})"
        return "configured"
    # Vendor CLI subscription paths: official binary login (no OAuth token scrape).
    if settings.provider == "anthropic_claude" or settings.provider == "anthropic_claude_code":
        from openharness.api.claude_cli_detect import claude_auth_status

        status = claude_auth_status()
        if status.ready:
            label = status.subscription_type or status.auth_method or "claude-code"
            return f"configured (claude-code {label})"
        if not status.cli_path:
            return "missing (install Claude Code CLI)"
        return "missing (run `claude auth login`)"
    if settings.provider in {"openai_codex", "codex_cli"}:
        from openharness.api.codex_cli_engine import codex_cli_status

        ready, detail, _path = codex_cli_status()
        return f"configured (codex-cli)" if ready else f"missing ({detail[:80]})"
    if settings.provider in {"grok", "grok_cli", "xai_grok"}:
        from openharness.api.grok_cli_engine import grok_cli_status

        ready, detail, _path = grok_cli_status()
        return f"configured (grok-cli)" if ready else f"missing ({detail[:80]})"
    if settings.provider in {"antigravity", "google_antigravity", "agy"}:
        from openharness.api.antigravity_cli_engine import antigravity_cli_status

        ready, detail, _path = antigravity_cli_status()
        return f"configured (antigravity-cli)" if ready else f"missing ({detail[:80]})"
    try:
        resolved = settings.resolve_auth()
    except ValueError as exc:
        if settings.provider == "openai_codex":
            return "missing (run `codex login`)"
        if settings.provider == "anthropic_claude":
            binding = load_external_binding("anthropic_claude")
            if binding is not None:
                external_state = describe_external_binding(binding)
                if external_state.state != "missing":
                    return external_state.state
            message = str(exc)
            if "third-party" in message:
                return "invalid base_url"
            return "missing (run `claude auth login`)"
        return "missing"
    if resolved.source.startswith("external:"):
        return f"configured ({resolved.source.removeprefix('external:')})"
    return "configured"


# ---------------------------------------------------------------------------
# Multimodal (vision) capability detection
# ---------------------------------------------------------------------------

# Known multimodal model patterns (lowercase, regex).
# These models can accept image input natively.
_MULTIMODAL_MODEL_PATTERNS: list[re.Pattern[str]] = [
    # Anthropic Claude 3+ (all Claude 3 and later support images)
    re.compile(r"^claude-3(?:\.\d+)?(?:-sonnet|-opus|-haiku)?"),
    re.compile(r"^claude-(?:sonnet|opus|haiku)-\d"),
    # OpenAI GPT-4o / o-series
    re.compile(r"^gpt-4o"),
    re.compile(r"^o[1349]-"),
    # Google Gemini
    re.compile(r"^gemini-(?:pro-)?vision"),
    re.compile(r"^gemini-2\.\d+"),
    # Qwen / DashScope VL series
    re.compile(r"^qwen-vl"),
    re.compile(r"^qwen2\.5?-vl"),
    re.compile(r"^qvq-"),
    # DeepSeek VL
    re.compile(r"^deepseek-vl"),
    re.compile(r"^deepseek-vision"),
    # Open-source multimodal
    re.compile(r"^llava"),
    re.compile(r"^cogvlm"),
    re.compile(r"^internvl"),
    re.compile(r"^glm-4v"),
    # Moonshot / Kimi (k2.5 supports images)
    re.compile(r"^kimi-k2\.5"),
    # StepFun (阶跃星辰) — Step-2 and Step-1v support images
    re.compile(r"^step-2"),
    re.compile(r"^step-1v"),
    # MiniMax VL
    re.compile(r"^minimax-vl"),
    # Zhipu GLM-4V
    re.compile(r"^glm-4v"),
    # Mistral Pixtral
    re.compile(r"^pixtral"),
    # Groq vision models (llama-3.2-vision, etc.)
    re.compile(r"vision"),
    # Generic: model names containing "vl" or "vision" as a word boundary
    re.compile(r"(?:^|[-\s/])vl(?:$|[-\s])"),
]


def is_model_multimodal(model: str) -> bool:
    """Return True when the model name indicates multimodal (vision) capability.

    This is a heuristic based on known model naming conventions.  It errs on
    the side of returning False for unknown models so that the image-to-text
    fallback tool is used rather than silently failing.
    """
    normalized = model.strip().lower()
    # Strip provider prefix like "anthropic/" or "openai/"
    if "/" in normalized:
        normalized = normalized.split("/", 1)[-1]
    return any(pattern.search(normalized) is not None for pattern in _MULTIMODAL_MODEL_PATTERNS)
