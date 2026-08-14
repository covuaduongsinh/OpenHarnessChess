"use client";

import { useEffect, useMemo, useState } from "react";

type ProviderInfo = {
  id: string;
  label: string;
  ready: boolean;
  binary: string | null;
  detail: string;
};

type LiveResult = {
  ok: boolean;
  error?: string;
  provider?: string;
  provider_label?: string;
  binary?: string;
  total_ms?: number;
  created?: string;
  saved?: string;
  game?: {
    white: string;
    black: string;
    event: string;
    moves: string[];
    move_count: number;
  };
  steps?: {
    t_ms: number;
    name: string;
    status: string;
    detail: string;
    binary?: string;
    prompt_excerpt?: string;
    duration_ms?: number;
    error?: string;
    fen?: string;
    san?: string;
    kinds?: string[];
  }[];
  plies?: {
    ply: number;
    san: string;
    side: string;
    signals: string[];
    fen_before: string;
    fen_after: string;
  }[];
  moments?: {
    kind: string;
    severity: string;
    ply: number;
    san: string;
    fen: string;
    note: string;
    bloom: { remember: string; apply: string; analyze: string };
  }[];
  selected_moment?: { fen: string; san: string; kind: string };
  prompt?: string;
  llm?: {
    status: string;
    response?: string;
    error?: string;
    duration_ms?: number;
    label?: string;
  };
};

const PROVIDERS = [
  { id: "antigravity", label: "Antigravity (agy)", color: "bg-blue-600" },
  { id: "claude", label: "Claude Code", color: "bg-orange-600" },
  { id: "grok", label: "Grok Build", color: "bg-zinc-900" },
  { id: "codex", label: "Codex CLI", color: "bg-emerald-700" },
] as const;

const SAMPLE_PGN = `[Event "OHCC Live Demo"]
[Site "CLB Co vua Duong Sinh"]
[White "HocVien"]
[Black "ThayTuong"]
[Result "0-1"]

1. f3 e5 2. g4 Qh4# 0-1
`;

function statusClass(s: string) {
  if (s === "ok") return "bg-emerald-100 text-emerald-800";
  if (s === "running") return "bg-sky-100 text-sky-900";
  if (s === "skipped") return "bg-amber-100 text-amber-900";
  return "bg-rose-100 text-rose-800";
}

function stepTitle(name: string): string {
  const map: Record<string, string> = {
    probe_cli: "1. Kiểm tra CLI model",
    parse_pgn: "2. Parse PGN",
    replay: "3. Replay nước đi (SAN → FEN)",
    detect_moments: "4. Heuristic bắt khoảnh khắc dạy",
    select_moment: "5. Chọn moment gửi LLM",
    build_prompt: "6. Dựng prompt Thầy Tường",
    llm_start: "7. Bắt đầu gọi LLM CLI",
    llm_finish: "8. LLM trả kết quả",
  };
  return map[name] || name;
}

export function LiveAnalyzeForm() {
  const [pgn, setPgn] = useState(SAMPLE_PGN);
  const [provider, setProvider] = useState<string>("claude");
  const [timeoutSec, setTimeoutSec] = useState(180);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LiveResult | null>(null);
  const [probes, setProbes] = useState<ProviderInfo[]>([]);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    fetch("/api/live-analyze")
      .then((r) => r.json())
      .then((d) => {
        if (d.providers) setProbes(d.providers);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!loading) return;
    setElapsed(0);
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, [loading]);

  const probeMap = useMemo(() => {
    const m = new Map<string, ProviderInfo>();
    for (const p of probes) m.set(p.id, p);
    return m;
  }, [probes]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/live-analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pgn,
          provider,
          timeout: timeoutSec,
          maxMoments: 4,
        }),
      });
      const data = (await res.json()) as LiveResult;
      if (!res.ok && !data.steps) {
        setError(data.error || `HTTP ${res.status}`);
      } else {
        setResult(data);
        if (!data.ok) setError(data.error || data.llm?.error || "Phân tích chưa thành công");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} className="card space-y-4">
        <div>
          <h3 className="text-lg font-bold text-board-accent">
            Phân tích live: PGN → pipeline → 1 model LLM
          </h3>
          <p className="mt-1 text-sm text-ink-800/70">
            Dán PGN, chọn đúng một provider, bấm chạy. Hệ thống hiển thị từng bước từ
            parse đến phản hồi Thầy Tường.
          </p>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-semibold">PGN</span>
          <textarea
            value={pgn}
            onChange={(e) => setPgn(e.target.value)}
            rows={10}
            className="w-full rounded-xl border border-ink-100 bg-ink-50 p-3 font-mono text-xs leading-relaxed outline-none ring-board-accent focus:ring-2"
            placeholder="Dán PGN vào đây…"
            required
          />
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold">Chọn model (1)</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {PROVIDERS.map((p) => {
              const st = probeMap.get(p.id);
              const ready = st?.ready;
              return (
                <label
                  key={p.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                    provider === p.id
                      ? "border-board-accent bg-board-accent/5 ring-2 ring-board-accent/30"
                      : "border-ink-100 bg-white hover:border-board-accent/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="provider"
                    value={p.id}
                    checked={provider === p.id}
                    onChange={() => setProvider(p.id)}
                    className="mt-1"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold text-white ${p.color}`}
                      >
                        {p.id}
                      </span>
                      <span className="font-semibold">{p.label}</span>
                      {st ? (
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            ready
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {ready ? "CLI sẵn sàng" : "chưa sẵn sàng"}
                        </span>
                      ) : null}
                    </span>
                    {st?.binary ? (
                      <span className="mt-1 block truncate font-mono text-[10px] text-ink-800/50">
                        {st.binary}
                      </span>
                    ) : null}
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="font-semibold">Timeout LLM (giây)</span>
            <input
              type="number"
              min={30}
              max={300}
              value={timeoutSec}
              onChange={(e) => setTimeoutSec(Number(e.target.value) || 180)}
              className="mt-1 block w-28 rounded-lg border border-ink-100 px-2 py-1.5"
            />
          </label>
          <button
            type="button"
            className="rounded-full border border-ink-200 px-4 py-2 text-sm"
            onClick={() => setPgn(SAMPLE_PGN)}
          >
            Dùng PGN mẫu Fool&apos;s Mate
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-full bg-board-accent px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {loading
              ? `Đang phân tích… ${elapsed}s (chờ CLI ${provider})`
              : `Chạy phân tích với ${provider}`}
          </button>
        </div>
        {error ? (
          <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-900">
            {error}
          </div>
        ) : null}
      </form>

      {result ? (
        <div className="space-y-4">
          {/* Timeline */}
          <section className="card space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-bold">Diễn biến từ đầu đến cuối</h3>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="badge">{result.provider_label || result.provider}</span>
                {result.total_ms != null ? (
                  <span className="badge">tổng {result.total_ms} ms</span>
                ) : null}
                {result.ok ? (
                  <span className="badge bg-emerald-100 text-emerald-800">ok</span>
                ) : (
                  <span className="badge bg-rose-100 text-rose-800">lỗi / incomplete</span>
                )}
              </div>
            </div>
            {result.game ? (
              <p className="text-sm text-ink-800/70">
                {result.game.event} · {result.game.white} vs {result.game.black} ·{" "}
                {result.game.move_count} nước
              </p>
            ) : null}

            <ol className="space-y-3 border-l-2 border-board-accent/30 pl-4">
              {(result.steps || []).map((s, i) => (
                <li key={`${s.name}-${i}`} className="relative">
                  <span className="absolute -left-[1.4rem] top-1 h-3 w-3 rounded-full border-2 border-board-accent bg-white" />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold">{stepTitle(s.name)}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${statusClass(s.status)}`}
                    >
                      {s.status}
                    </span>
                    <span className="text-[11px] text-ink-800/45">@{s.t_ms}ms</span>
                  </div>
                  <p className="mt-1 text-sm text-ink-800/90">{s.detail}</p>
                  {s.prompt_excerpt ? (
                    <p className="mt-1 rounded bg-ink-50 p-2 font-mono text-[11px] text-ink-800/70">
                      {s.prompt_excerpt}…
                    </p>
                  ) : null}
                  {s.fen ? (
                    <p className="mt-1 break-all font-mono text-[10px] text-ink-800/50">
                      FEN: {s.fen}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          </section>

          {/* Replay table */}
          {result.plies && result.plies.length > 0 ? (
            <section className="card space-y-2">
              <h3 className="font-semibold">Replay + tín hiệu heuristic</h3>
              <div className="max-h-64 overflow-auto rounded-xl border border-ink-100">
                <table className="min-w-full text-left text-xs">
                  <thead className="bg-ink-100/80">
                    <tr>
                      <th className="px-2 py-2">Ply</th>
                      <th className="px-2 py-2">SAN</th>
                      <th className="px-2 py-2">Bên</th>
                      <th className="px-2 py-2">Signals</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.plies.map((p) => (
                      <tr
                        key={p.ply}
                        className={
                          p.signals.length ? "bg-amber-50/80" : undefined
                        }
                      >
                        <td className="px-2 py-1 font-mono">{p.ply}</td>
                        <td className="px-2 py-1 font-mono font-semibold">{p.san}</td>
                        <td className="px-2 py-1">
                          {p.side === "white" ? "Trắng" : "Đen"}
                        </td>
                        <td className="px-2 py-1">
                          {p.signals.length ? p.signals.join(", ") : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {/* Moments bloom */}
          {result.moments && result.moments.length > 0 ? (
            <section className="card space-y-3">
              <h3 className="font-semibold">Teaching moments (trước khi gọi LLM)</h3>
              {result.moments.map((m) => (
                <div
                  key={`${m.kind}-${m.ply}`}
                  className="rounded-xl border border-ink-100 bg-ink-50/70 p-3 text-sm"
                >
                  <div className="flex flex-wrap gap-2">
                    <span className="badge">{m.kind}</span>
                    <span className="badge">{m.severity}</span>
                    <span className="badge">ply {m.ply}</span>
                    <span className="badge font-mono">{m.san}</span>
                  </div>
                  <p className="mt-2 text-xs text-ink-800/60">{m.note}</p>
                  <ul className="mt-2 space-y-1 text-sm">
                    <li>
                      <strong>Nhận biết:</strong> {m.bloom.remember}
                    </li>
                    <li>
                      <strong>Áp dụng:</strong> {m.bloom.apply}
                    </li>
                    <li>
                      <strong>Phân tích:</strong> {m.bloom.analyze}
                    </li>
                  </ul>
                </div>
              ))}
            </section>
          ) : null}

          {/* LLM final */}
          <section
            className={`overflow-hidden rounded-2xl border-2 shadow-sm ${
              result.ok ? "border-board-accent/40" : "border-rose-200"
            }`}
          >
            <header
              className={`px-4 py-3 text-white ${
                PROVIDERS.find((p) => p.id === result.provider)?.color ||
                "bg-board-accent"
              }`}
            >
              <p className="text-[10px] font-bold uppercase tracking-widest opacity-80">
                Kết quả cuối — model đã chọn
              </p>
              <h3 className="text-xl font-bold">
                {result.provider_label || result.provider}
              </h3>
              <p className="text-xs text-white/80">
                {result.binary} · {result.llm?.duration_ms ?? "—"} ms · moment{" "}
                {result.selected_moment?.san}
              </p>
            </header>
            <div className="space-y-3 bg-white p-4">
              {result.prompt ? (
                <details>
                  <summary className="cursor-pointer text-sm font-semibold text-board-accent">
                    Prompt đã gửi cho model
                  </summary>
                  <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-50">
                    {result.prompt}
                  </pre>
                </details>
              ) : null}
              {result.llm?.response ? (
                <div className="rounded-xl bg-board-accent/5 p-4">
                  <p className="mb-2 text-xs font-bold uppercase tracking-wide text-board-accent">
                    Phản hồi Thầy Tường từ {result.provider_label}
                  </p>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {result.llm.response}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-rose-800">
                  {result.llm?.error || result.error || "Không có phản hồi LLM"}
                </p>
              )}
              {result.saved ? (
                <p className="text-[11px] text-ink-800/50">Đã lưu: {result.saved}</p>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
