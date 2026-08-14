import { MiniBoard } from "@/components/MiniBoard";
import {
  bloomLabel,
  kindLabel,
  type AnalysisMoment,
  type GameAnalysis,
} from "@/lib/analysis";

export function EngineLegend() {
  return (
    <div className="card space-y-2 text-sm">
      <h3 className="font-semibold text-board-accent">Mô hình / engine phân tích (MIT)</h3>
      <ul className="list-disc space-y-1 pl-5 text-ink-800/90">
        <li>
          <strong>Heuristic OHCC</strong> — phát hiện chiếu / bắt / quân treo / mate khi
          replay PGN (<code>ohcc.chess_core</code>).
        </li>
        <li>
          <strong>Scaffolding Bloom</strong> — mỗi khoảnh khắc → 3 câu hỏi Socratic
          (Nhận biết → Áp dụng → Phân tích).
        </li>
        <li>
          <strong>Arasan (UCI, MIT)</strong> — eval drop / blunder khi bật{" "}
          <code>--arasan</code> + binary. <em>Không</em> dùng Stockfish/Maia (GPL).
        </li>
        <li>
          <strong>Thầy Tường</strong> — persona coach: không dump điểm eval thô cho học
          viên nhỏ.
        </li>
      </ul>
    </div>
  );
}

export function MomentCard({ moment }: { moment: AnalysisMoment }) {
  return (
    <article className="rounded-xl border border-ink-100 bg-ink-50/80 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap gap-2">
            <span className="badge">{kindLabel(moment.momentKind)}</span>
            <span className="badge">severity: {moment.severity}</span>
            {moment.plyIndex != null ? (
              <span className="badge">ply {moment.plyIndex}</span>
            ) : null}
            {moment.san ? (
              <span className="badge font-mono">SAN {moment.san}</span>
            ) : null}
          </div>
          <p className="break-all font-mono text-[11px] text-ink-800/60">
            FEN: {moment.fen}
          </p>
          <div className="space-y-3">
            {moment.layers.map((layer) => (
              <div
                key={layer.path}
                className="rounded-lg border border-white bg-white p-3 shadow-sm"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-board-accent">
                  Bloom · {bloomLabel(layer.bloom)}
                </p>
                <p className="mt-1 text-sm font-medium">{layer.title}</p>
                <p className="mt-2 text-sm leading-relaxed text-ink-800/90">
                  {layer.prompt || "(không trích được câu hỏi)"}
                </p>
                <p className="mt-2 text-[11px] text-ink-800/45">{layer.path}</p>
              </div>
            ))}
          </div>
        </div>
        {moment.fen ? (
          <div className="shrink-0">
            <MiniBoard fen={moment.fen} size={176} />
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function GameAnalysisCard({
  game,
  defaultOpen = false,
}: {
  game: GameAnalysis;
  defaultOpen?: boolean;
}) {
  const white = game.headers.White || "?";
  const black = game.headers.Black || "?";

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">{game.gameName}</h3>
          <p className="text-sm text-ink-800/70">
            {white} vs {black} · <code>{game.gameFile}</code>
          </p>
          <p className="mt-1 text-xs text-ink-800/55">{game.engineNote}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="badge">{game.moments.length} khoảnh khắc</span>
          <span className="badge">{game.puzzleCount} puzzle Bloom</span>
        </div>
      </div>

      {!game.moments.length ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Chưa có phân tích scaffolding cho ván này. Chạy:{" "}
          <code className="rounded bg-white px-1">
            python -m ohcc.scaffolding --pgn vault/04-games/{game.gameFile} --vault vault
          </code>
        </p>
      ) : (
        <details open={defaultOpen} className="group">
          <summary className="cursor-pointer text-sm font-semibold text-board-accent">
            Xem mô hình phân tích Socratic / Bloom ({game.moments.length} moments)
          </summary>
          <div className="mt-4 space-y-4">
            {game.moments.map((m) => (
              <MomentCard key={m.key} moment={m} />
            ))}
          </div>
        </details>
      )}

      <details>
        <summary className="cursor-pointer text-sm font-medium text-ink-800/70">
          PGN gốc
        </summary>
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-50">
          {game.pgnPreview}
        </pre>
      </details>
    </section>
  );
}
