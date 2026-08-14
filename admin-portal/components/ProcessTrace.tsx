import { MiniBoard } from "@/components/MiniBoard";
import { bloomLabel, kindLabel } from "@/lib/analysis";
import type { AnalysisTrace, TracePly, TraceStage } from "@/lib/traces";

function statusStyle(status: string): string {
  if (status === "ok") return "bg-emerald-100 text-emerald-800";
  if (status === "skipped") return "bg-amber-100 text-amber-900";
  if (status === "policy") return "bg-sky-100 text-sky-900";
  return "bg-ink-100 text-ink-800";
}

function stripMd(s: string): string {
  return s.replace(/\*\*/g, "").replace(/`/g, "");
}

export function GlobalPipelineBanner() {
  const steps = [
    { n: "1", title: "Parse PGN", model: "chess_core.pgn" },
    { n: "2", title: "Replay SAN→FEN", model: "board + movegen" },
    { n: "3", title: "Bắt tín hiệu", model: "heuristic detector" },
    { n: "4", title: "Eval (tuỳ chọn)", model: "Arasan UCI" },
    { n: "5", title: "Bloom ×3", model: "scaffolding.questions" },
    { n: "6", title: "Giọng Thầy Tường", model: "persona Socratic" },
  ];
  return (
    <div className="card overflow-x-auto">
      <h3 className="mb-3 font-semibold text-board-accent">
        Quy trình model (pipeline) — luôn chạy theo thứ tự này
      </h3>
      <div className="flex min-w-[720px] items-stretch gap-2">
        {steps.map((s, i) => (
          <div key={s.n} className="flex flex-1 items-stretch gap-2">
            <div className="flex-1 rounded-xl border border-board-accent/20 bg-board-accent/5 p-3">
              <p className="text-xs font-bold text-board-accent">Bước {s.n}</p>
              <p className="mt-1 text-sm font-semibold">{s.title}</p>
              <p className="mt-1 font-mono text-[10px] text-ink-800/60">{s.model}</p>
            </div>
            {i < steps.length - 1 ? (
              <div className="flex items-center text-board-accent">→</div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function StageRow({ stage }: { stage: TraceStage }) {
  return (
    <li className="relative border-l-2 border-board-accent/30 pl-5 pb-6 last:pb-0">
      <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-board-accent bg-white" />
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold">
          Bước {stage.id}. {stage.title}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${statusStyle(stage.status)}`}
        >
          {stage.status}
        </span>
      </div>
      <p className="mt-1 font-mono text-[11px] text-board-accent">{stage.model}</p>
      <p className="mt-2 text-sm leading-relaxed text-ink-800/90">{stage.detail}</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg bg-ink-900 p-2 font-mono text-[11px] text-emerald-200">
          <span className="text-ink-50/50">IN · </span>
          {typeof stage.io.input === "string"
            ? stage.io.input
            : JSON.stringify(stage.io.input)}
        </div>
        <div className="rounded-lg bg-ink-900 p-2 font-mono text-[11px] text-sky-200">
          <span className="text-ink-50/50">OUT · </span>
          {typeof stage.io.output === "string"
            ? stage.io.output
            : JSON.stringify(stage.io.output)}
        </div>
      </div>
    </li>
  );
}

function PlyRow({ ply }: { ply: TracePly }) {
  const hot = ply.selected_as_teaching_moment || ply.signals.length > 0;
  return (
    <tr className={hot ? "bg-amber-50/80" : undefined}>
      <td className="px-2 py-1.5 font-mono text-xs">{ply.ply}</td>
      <td className="px-2 py-1.5 font-mono text-xs font-semibold">{ply.san}</td>
      <td className="px-2 py-1.5 text-xs">{ply.side === "white" ? "Trắng" : "Đen"}</td>
      <td className="px-2 py-1.5 text-xs">
        {ply.signals.length ? (
          <div className="flex flex-wrap gap-1">
            {ply.signals.map((s) => (
              <span key={s.code + s.label} className="badge">
                {s.label}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-ink-800/40">—</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-xs">
        {ply.selected_as_teaching_moment ? (
          <span className="font-semibold text-board-accent">★ chọn dạy</span>
        ) : (
          "—"
        )}
      </td>
    </tr>
  );
}

export function ProcessTracePanel({
  trace,
  defaultOpen = true,
}: {
  trace: AnalysisTrace;
  defaultOpen?: boolean;
}) {
  return (
    <div className="space-y-4 rounded-2xl border-2 border-board-accent/30 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-board-accent">
            Nhật ký chạy model
          </p>
          <h3 className="text-lg font-bold">
            {trace.event} · {trace.white} vs {trace.black}
          </h3>
          <p className="text-sm text-ink-800/70">
            File <code>{trace.gameFile}</code> · {trace.moveCount} nước ·{" "}
            {trace.plies.length} ply đã replay
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {trace.models_summary.map((m) => (
            <span
              key={m.name}
              className={`badge ${m.active === false ? "opacity-60" : ""}`}
              title={m.role}
            >
              {m.name}
              {m.active === false ? " (tắt)" : ""}
            </span>
          ))}
        </div>
      </div>

      {/* Stage timeline */}
      <details open={defaultOpen}>
        <summary className="cursor-pointer text-sm font-semibold text-board-accent">
          1) Chuỗi bước model (IN → xử lý → OUT)
        </summary>
        <ol className="mt-4 ml-1">
          {trace.stages.map((s) => (
            <StageRow key={s.id} stage={s} />
          ))}
        </ol>
      </details>

      {/* Move-by-move signal table */}
      <details open={defaultOpen}>
        <summary className="cursor-pointer text-sm font-semibold text-board-accent">
          2) Replay từng nước + tín hiệu heuristic (model detector)
        </summary>
        <div className="mt-3 overflow-x-auto rounded-xl border border-ink-100">
          <table className="min-w-full text-left">
            <thead className="bg-ink-100/80 text-xs uppercase text-ink-800/70">
              <tr>
                <th className="px-2 py-2">Ply</th>
                <th className="px-2 py-2">SAN</th>
                <th className="px-2 py-2">Bên</th>
                <th className="px-2 py-2">Tín hiệu model bắt được</th>
                <th className="px-2 py-2">Teaching?</th>
              </tr>
            </thead>
            <tbody>
              {trace.plies.map((p) => (
                <PlyRow key={p.ply} ply={p} />
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-ink-800/55">
          Hàng tô vàng = có tín hiệu hoặc được chọn làm khoảnh khắc dạy.
        </p>
      </details>

      {/* Moments with rules + bloom */}
      <details open={defaultOpen}>
        <summary className="cursor-pointer text-sm font-semibold text-board-accent">
          3) Khoảnh khắc được model chọn + rule kích hoạt + output Bloom
        </summary>
        <div className="mt-4 space-y-4">
          {!trace.moments.length ? (
            <p className="text-sm text-ink-800/70">Không có teaching moment.</p>
          ) : (
            trace.moments.map((m, idx) => (
              <div
                key={`${m.kind}-${m.ply}-${idx}`}
                className="rounded-xl border border-ink-100 bg-ink-50/70 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap gap-2">
                      <span className="badge">{kindLabel(m.kind)}</span>
                      <span className="badge">severity: {m.severity}</span>
                      <span className="badge">ply {m.ply}</span>
                      <span className="badge font-mono">{m.san}</span>
                    </div>
                    <div className="rounded-lg border border-dashed border-board-accent/40 bg-white p-3">
                      <p className="text-xs font-semibold text-board-accent">
                        Rule model đã bật
                      </p>
                      <ul className="mt-1 list-disc pl-5 text-sm text-ink-800/90">
                        {m.detection_rules.map((r) => (
                          <li key={r} className="font-mono text-xs">
                            {r}
                          </li>
                        ))}
                      </ul>
                      <p className="mt-2 text-xs text-ink-800/60">{m.note}</p>
                      {m.drop_cp != null ? (
                        <p className="mt-1 text-xs">
                          Arasan drop_cp: <strong>{m.drop_cp}</strong>
                        </p>
                      ) : (
                        <p className="mt-1 text-xs text-amber-800">
                          Arasan: không chạy (demo heuristic-only)
                        </p>
                      )}
                    </div>
                    <div className="space-y-2">
                      {(
                        [
                          ["remember", m.bloom_outputs.remember],
                          ["apply", m.bloom_outputs.apply],
                          ["analyze", m.bloom_outputs.analyze],
                        ] as const
                      ).map(([bloom, q]) => (
                        <div
                          key={bloom}
                          className="rounded-lg border border-white bg-white p-3 shadow-sm"
                        >
                          <p className="text-xs font-semibold uppercase tracking-wide text-board-accent">
                            Output model Bloom · {bloomLabel(bloom)}
                          </p>
                          <p className="mt-1 text-sm leading-relaxed">
                            {stripMd(q)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                  {m.fen ? <MiniBoard fen={m.fen} size={168} /> : null}
                </div>
              </div>
            ))
          )}
        </div>
      </details>
    </div>
  );
}
