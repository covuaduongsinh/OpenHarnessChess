import fs from "fs";
import path from "path";
import { vaultRoot } from "@/lib/vault";

export type ProviderProbe = {
  id: string;
  label: string;
  ready: boolean;
  binary: string | null;
  detail: string;
};

export type LlmReviewRow = {
  provider: string;
  label: string;
  status: string;
  binary?: string | null;
  duration_ms?: number;
  model_note?: string;
  prompt_excerpt?: string;
  response?: string;
  error?: string;
  game_file?: string;
  fen?: string;
  created?: string;
};

export type LlmReviewBundle = {
  game: string;
  fen: string;
  san_moment: string;
  created: string;
  providers_probed?: ProviderProbe[];
  reviews: LlmReviewRow[];
  path: string;
};

const PROVIDER_META: Record<
  string,
  { color: string; short: string; stack: string }
> = {
  antigravity: {
    color: "bg-blue-600",
    short: "AGY",
    stack: "Google Antigravity CLI (`agy`) — subscription",
  },
  claude: {
    color: "bg-orange-600",
    short: "CLD",
    stack: "Anthropic Claude Code CLI — subscription",
  },
  grok: {
    color: "bg-zinc-900",
    short: "GRK",
    stack: "xAI Grok Build CLI — SuperGrok / X Premium+",
  },
  codex: {
    color: "bg-emerald-700",
    short: "CDX",
    stack: "OpenAI Codex CLI — ChatGPT subscription",
  },
};

export function providerMeta(id: string) {
  return (
    PROVIDER_META[id] || {
      color: "bg-ink-800",
      short: id.slice(0, 3).toUpperCase(),
      stack: id,
    }
  );
}

function llmDir(): string {
  return path.join(vaultRoot(), "_meta", "llm-reviews");
}

export function loadProviderStatus(): ProviderProbe[] {
  const f = path.join(llmDir(), "providers-status.json");
  if (!fs.existsSync(f)) return [];
  try {
    const raw = JSON.parse(fs.readFileSync(f, "utf8"));
    return (raw.providers || []) as ProviderProbe[];
  } catch {
    return [];
  }
}

export function listLlmReviewBundles(): LlmReviewBundle[] {
  const dir = llmDir();
  if (!fs.existsSync(dir)) return [];
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith("-llm-latest.json"))
    .sort()
    .reverse();
  // also include timestamped if no latest
  const more = fs
    .readdirSync(dir)
    .filter((f) => f.includes("-llm-") && f.endsWith(".json") && !f.endsWith("-latest.json"))
    .sort()
    .reverse();

  const seen = new Set<string>();
  const bundles: LlmReviewBundle[] = [];
  for (const f of [...files, ...more]) {
    try {
      const full = path.join(dir, f);
      const raw = JSON.parse(fs.readFileSync(full, "utf8"));
      const key = raw.game || f;
      if (seen.has(key) && f.includes("-latest")) {
        // prefer latest
      }
      if (seen.has(key)) continue;
      seen.add(key);
      bundles.push({
        game: raw.game,
        fen: raw.fen,
        san_moment: raw.san_moment,
        created: raw.created,
        providers_probed: raw.providers_probed,
        reviews: raw.reviews || [],
        path: path.relative(vaultRoot(), full).replace(/\\/g, "/"),
      });
    } catch {
      /* skip */
    }
  }
  return bundles;
}
