import Link from "next/link";
import { PageHeader } from "@/components/DocList";
import { ProcessTracePanel } from "@/components/ProcessTrace";
import { buildGameAnalyses } from "@/lib/analysis";
import { loadTrace } from "@/lib/traces";

export const dynamic = "force-dynamic";

export default function GamesPage() {
  const games = buildGameAnalyses();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ván cờ / PGN"
        subtitle="Kèm nhật ký chạy model (parse → replay → heuristic → Bloom). Chi tiết: menu Phân tích."
      />

      <div className="flex flex-wrap gap-2 text-sm">
        <Link
          href="/analysis"
          className="rounded-full bg-board-accent px-4 py-2 font-medium text-white hover:opacity-90"
        >
          Nhật ký model đầy đủ
        </Link>
        <Link
          href="/puzzles"
          className="rounded-full border border-board-accent px-4 py-2 font-medium text-board-accent hover:bg-board-accent/5"
        >
          Thư viện puzzle Bloom
        </Link>
      </div>

      {!games.length ? (
        <div className="card text-sm text-ink-800/70">
          Chưa có PGN. Chạy <code>python scripts/ohcc/run_local_demo.py</code>.
        </div>
      ) : (
        <ul className="space-y-6">
          {games.map((g) => {
            const trace = loadTrace(g.gameFile);
            return (
              <li key={g.gameFile} className="space-y-2">
                {trace ? (
                  <ProcessTracePanel trace={trace} defaultOpen={false} />
                ) : (
                  <div className="card text-sm">
                    <p className="font-semibold">{g.gameName}</p>
                    <p className="text-ink-800/70">
                      Chưa có process trace. Chạy{" "}
                      <code>python scripts/ohcc/export_analysis_traces.py</code>
                    </p>
                    <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-ink-900 p-2 text-xs text-ink-50">
                      {g.pgnPreview.slice(0, 800)}
                    </pre>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
