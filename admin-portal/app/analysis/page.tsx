import Link from "next/link";
import { PageHeader } from "@/components/DocList";
import { GlobalPipelineBanner, ProcessTracePanel } from "@/components/ProcessTrace";
import { analysisOverview } from "@/lib/analysis";
import { listTraces } from "@/lib/traces";

export const dynamic = "force-dynamic";

export default function AnalysisPage() {
  const overview = analysisOverview();
  const traces = listTraces();
  const traceByFile = new Map(traces.map((t) => [t.gameFile, t]));

  return (
    <div className="space-y-8">
      <PageHeader
        title="Phân tích ván đấu — nhật ký model"
        subtitle="Thấy rõ từng bước: parse → replay → heuristic → (Arasan) → Bloom → Thầy Tường."
      />

      <GlobalPipelineBanner />

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <p className="text-sm text-ink-800/70">Ván trong vault</p>
          <p className="mt-1 text-3xl font-bold text-board-accent">
            {overview.games.length}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-ink-800/70">Trace đã export</p>
          <p className="mt-1 text-3xl font-bold text-board-accent">{traces.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-ink-800/70">Khoảnh khắc dạy</p>
          <p className="mt-1 text-3xl font-bold text-board-accent">
            {overview.totalMoments}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-ink-800/70">Puzzle Bloom</p>
          <p className="mt-1 text-3xl font-bold text-board-accent">
            {overview.totalPuzzles}
          </p>
        </div>
      </section>

      <section className="card space-y-2 text-sm">
        <h3 className="font-semibold">Làm mới nhật ký model</h3>
        <p className="text-ink-800/80">
          Trace được sinh bởi Python pipeline (cùng code production), không phải UI giả:
        </p>
        <pre className="overflow-x-auto rounded-lg bg-ink-900 p-3 text-xs text-ink-50">
{`python scripts/ohcc/export_analysis_traces.py
# → vault/_meta/analysis-traces/*.json`}
        </pre>
        <p>
          <Link href="/puzzles" className="text-board-accent hover:underline">
            Thư viện puzzle Bloom →
          </Link>
        </p>
      </section>

      <section className="space-y-6">
        <h3 className="text-lg font-semibold">Theo từng ván — process log</h3>
        {!traces.length ? (
          <div className="card text-sm text-amber-900 bg-amber-50">
            Chưa có file trace. Chạy{" "}
            <code>python scripts/ohcc/export_analysis_traces.py</code> rồi reload
            trang.
          </div>
        ) : (
          traces.map((t, i) => (
            <ProcessTracePanel key={t.gameFile} trace={t} defaultOpen={i === 0} />
          ))
        )}
      </section>

      {/* Fallback list if some games lack traces */}
      {overview.games.some((g) => !traceByFile.has(g.gameFile)) ? (
        <section className="card text-sm text-ink-800/70">
          <p className="font-medium">Ván chưa có trace:</p>
          <ul className="mt-2 list-disc pl-5">
            {overview.games
              .filter((g) => !traceByFile.has(g.gameFile))
              .map((g) => (
                <li key={g.gameFile}>{g.gameFile}</li>
              ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
