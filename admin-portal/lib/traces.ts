import fs from "fs";
import path from "path";
import { vaultRoot } from "@/lib/vault";

export type TraceSignal = {
  code: string;
  label: string;
  squares?: string[];
};

export type TracePly = {
  ply: number;
  san: string;
  side: string;
  fen_before: string;
  fen_after: string;
  signals: TraceSignal[];
  selected_as_teaching_moment: boolean;
};

export type TraceStage = {
  id: number;
  model: string;
  title: string;
  status: string;
  detail: string;
  io: { input: string | unknown; output: string | unknown };
};

export type TraceMoment = {
  kind: string;
  severity: string;
  ply: number;
  san: string;
  fen: string;
  note: string;
  drop_cp: number | null;
  detection_rules: string[];
  bloom_outputs: {
    remember: string;
    apply: string;
    analyze: string;
  };
};

export type AnalysisTrace = {
  gameFile: string;
  event: string;
  white: string;
  black: string;
  moveCount: number;
  moves: string[];
  stages: TraceStage[];
  plies: TracePly[];
  moments: TraceMoment[];
  models_summary: {
    name: string;
    license: string;
    role: string;
    active?: boolean;
  }[];
};

export function tracesDir(): string {
  return path.join(vaultRoot(), "_meta", "analysis-traces");
}

export function loadTrace(gameFile: string): AnalysisTrace | null {
  const stem = gameFile.replace(/\.pgn$/i, "").replace(/\.md$/i, "");
  const file = path.join(tracesDir(), `${stem}.json`);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8")) as AnalysisTrace;
}

export function listTraces(): AnalysisTrace[] {
  const dir = tracesDir();
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json") && f !== "index.json")
    .sort()
    .map((f) => {
      try {
        return JSON.parse(
          fs.readFileSync(path.join(dir, f), "utf8")
        ) as AnalysisTrace;
      } catch {
        return null;
      }
    })
    .filter((t): t is AnalysisTrace => t !== null);
}
