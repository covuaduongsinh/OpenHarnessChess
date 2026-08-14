import fs from "fs";
import path from "path";
import { listMarkdown, vaultRoot, type VaultDoc } from "@/lib/vault";

export type AnalysisMoment = {
  key: string;
  momentKind: string;
  plyIndex: number | null;
  san: string;
  severity: string;
  fen: string;
  sourcePgn: string;
  layers: {
    bloom: string;
    title: string;
    prompt: string;
    path: string;
  }[];
};

export type GameAnalysis = {
  gameFile: string;
  gameName: string;
  pgnPreview: string;
  headers: Record<string, string>;
  moments: AnalysisMoment[];
  puzzleCount: number;
  engineNote: string;
};

const KIND_VI: Record<string, string> = {
  mate: "Chiếu hết",
  check: "Nước chiếu",
  hanging: "Quân treo",
  capture: "Bắt quân",
  eval_drop: "Eval drop (Arasan)",
  annotated: "Ghi chú",
};

const BLOOM_VI: Record<string, string> = {
  remember: "Nhận biết",
  apply: "Áp dụng",
  analyze: "Phân tích",
};

export function kindLabel(kind: string): string {
  return KIND_VI[kind] || kind;
}

export function bloomLabel(bloom: string): string {
  return BLOOM_VI[bloom] || bloom;
}

export function listAllPuzzles(): VaultDoc[] {
  return [
    ...listMarkdown("03-puzzles/bloom-remember"),
    ...listMarkdown("03-puzzles/bloom-apply"),
    ...listMarkdown("03-puzzles/bloom-analyze"),
  ];
}

export function extractSocraticPrompt(body: string): string {
  const m = body.match(
    /## Câu hỏi gợi mở \(Socratic\)\s*\n+([\s\S]*?)(?=\n## |\n---|\s*$)/
  );
  if (m) return m[1].trim();
  // fallback: first non-heading paragraph after title
  const lines = body.split("\n").filter((l) => l.trim() && !l.startsWith("#"));
  return lines.slice(0, 3).join(" ").trim();
}

function sourceKey(source: string): string {
  const base = source.replace(/\\/g, "/").split("/").pop() || source;
  return base.toLowerCase();
}

export function listGameFiles(): string[] {
  const dir = path.join(vaultRoot(), "04-games");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".pgn") || f.endsWith(".md"))
    .sort();
}

export function parsePgnHeaders(text: string): Record<string, string> {
  const headers: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const m = line.match(/^\[(\w+)\s+"(.*)"\]\s*$/);
    if (m) headers[m[1]] = m[2];
  }
  return headers;
}

export function buildGameAnalyses(): GameAnalysis[] {
  const puzzles = listAllPuzzles();
  const games = listGameFiles();
  const bySource = new Map<string, VaultDoc[]>();

  for (const p of puzzles) {
    const src = String(p.data.source_pgn || "");
    const key = sourceKey(src);
    if (!key) continue;
    const list = bySource.get(key) || [];
    list.push(p);
    bySource.set(key, list);
  }

  return games.map((gameFile) => {
    const full = path.join(vaultRoot(), "04-games", gameFile);
    const text = fs.existsSync(full) ? fs.readFileSync(full, "utf8") : "";
    const headers = parsePgnHeaders(text);
    const key = sourceKey(gameFile);
    // match demo/name.pgn or name.pgn
    const related =
      bySource.get(key) ||
      bySource.get(`demo/${key}`) ||
      [...bySource.entries()]
        .filter(([k]) => k.endsWith(key) || key.endsWith(k))
        .flatMap(([, v]) => v);

    const momentMap = new Map<string, AnalysisMoment>();
    for (const doc of related) {
      const kind = String(doc.data.moment_kind || "unknown");
      const ply =
        typeof doc.data.ply_index === "number"
          ? doc.data.ply_index
          : Number(doc.data.ply_index) || null;
      const san = String(doc.data.san || "");
      const fen = String(doc.data.fen || "");
      const severity = String(doc.data.severity || "tip");
      const bloom = String(doc.data.bloom || "");
      const mkey = `${kind}|${ply}|${san}|${fen}`;
      let moment = momentMap.get(mkey);
      if (!moment) {
        moment = {
          key: mkey,
          momentKind: kind,
          plyIndex: ply,
          san,
          severity,
          fen,
          sourcePgn: String(doc.data.source_pgn || gameFile),
          layers: [],
        };
        momentMap.set(mkey, moment);
      }
      moment.layers.push({
        bloom,
        title: doc.title,
        prompt: extractSocraticPrompt(doc.body),
        path: doc.path,
      });
    }

    const moments = [...momentMap.values()].sort((a, b) => {
      const pa = a.plyIndex ?? 999;
      const pb = b.plyIndex ?? 999;
      return pa - pb;
    });
    // sort layers by bloom order
    const bloomOrder = { remember: 0, apply: 1, analyze: 2 };
    for (const m of moments) {
      m.layers.sort(
        (a, b) =>
          (bloomOrder[a.bloom as keyof typeof bloomOrder] ?? 9) -
          (bloomOrder[b.bloom as keyof typeof bloomOrder] ?? 9)
      );
    }

    return {
      gameFile,
      gameName: headers.Event || gameFile,
      pgnPreview: text.slice(0, 1200),
      headers,
      moments,
      puzzleCount: related.length,
      engineNote:
        "Heuristic + scaffolding (MIT). Arasan eval drops khi bật --arasan / ARASAN_PATH.",
    };
  });
}

export function analysisOverview() {
  const games = buildGameAnalyses();
  const totalMoments = games.reduce((n, g) => n + g.moments.length, 0);
  const totalPuzzles = games.reduce((n, g) => n + g.puzzleCount, 0);
  const kinds = new Map<string, number>();
  for (const g of games) {
    for (const m of g.moments) {
      kinds.set(m.momentKind, (kinds.get(m.momentKind) || 0) + 1);
    }
  }
  return {
    games,
    totalMoments,
    totalPuzzles,
    kinds: [...kinds.entries()].map(([kind, count]) => ({
      kind,
      label: kindLabel(kind),
      count,
    })),
  };
}
