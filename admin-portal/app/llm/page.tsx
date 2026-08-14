import Link from "next/link";
import { LiveAnalyzeForm } from "@/components/LiveAnalyzeForm";
import { MiniBoard } from "@/components/MiniBoard";
import { PageHeader } from "@/components/DocList";
import {
  listLlmReviewBundles,
  loadProviderStatus,
  providerMeta,
  type LlmReviewRow,
} from "@/lib/llmReviews";

export const dynamic = "force-dynamic";

function StatusPill({ ready }: { ready: boolean }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        ready ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
      }`}
    >
      {ready ? "CLI sẵn sàng" : "Chưa sẵn sàng"}
    </span>
  );
}

function ReviewCard({ review }: { review: LlmReviewRow }) {
  const meta = providerMeta(review.provider);
  const ok = review.status === "ok";
  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-sm">
      <header className={`${meta.color} px-4 py-3 text-white`}>
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest opacity-80">
              LLM provider
            </p>
            <h3 className="text-lg font-bold">{review.label}</h3>
          </div>
          <span className="rounded-lg bg-white/15 px-2 py-1 font-mono text-sm">
            {meta.short}
          </span>
        </div>
        <p className="mt-1 text-xs text-white/85">{meta.stack}</p>
      </header>
      <div className="flex flex-1 flex-col gap-2 p-4 text-sm">
        <div className="flex flex-wrap gap-2">
          <span
            className={`badge ${
              ok
                ? "bg-emerald-100 text-emerald-800"
                : review.status === "skipped"
                  ? "bg-amber-100 text-amber-900"
                  : "bg-rose-100 text-rose-800"
            }`}
          >
            status: {review.status}
          </span>
          {review.duration_ms != null ? (
            <span className="badge">{review.duration_ms} ms</span>
          ) : null}
        </div>
        {ok && review.response ? (
          <div className="max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-board-accent/5 p-3 text-sm">
            {review.response}
          </div>
        ) : (
          <p className="text-xs text-ink-800/55">{review.error || "—"}</p>
        )}
      </div>
    </article>
  );
}

export default function LlmPage() {
  const status = loadProviderStatus();
  const bundles = listLlmReviewBundles();
  const latest = bundles[0];

  return (
    <div className="space-y-10">
      <PageHeader
        title="LLM Coach — phân tích live"
        subtitle="Nhập PGN · chọn Antigravity / Claude / Grok / Codex · xem pipeline + kết quả coach từ đầu đến cuối."
      />

      {/* PRIMARY: interactive live analyze */}
      <LiveAnalyzeForm />

      <section className="card space-y-2 text-sm">
        <h3 className="font-semibold">Hai lớp phân tích trong OHCC</h3>
        <ul className="list-disc space-y-1 pl-5 text-ink-800/90">
          <li>
            <Link href="/analysis" className="text-board-accent underline">
              Phân tích cờ
            </Link>{" "}
            — heuristic MIT (không LLM): replay, moment, Bloom.
          </li>
          <li>
            <strong>LLM Coach (trang này)</strong> — model ngôn ngữ thật qua CLI
            subscription, đóng vai Thầy Tường.
          </li>
        </ul>
      </section>

      <section>
        <h3 className="mb-3 text-lg font-semibold">Trạng thái CLI (lần probe gần nhất)</h3>
        {!status.length ? (
          <div className="card text-sm text-ink-800/70">
            Chưa có snapshot. Form live ở trên sẽ probe khi mở trang; hoặc chạy{" "}
            <code>python scripts/ohcc/run_llm_coach_demo.py</code>.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {status.map((p) => {
              const meta = providerMeta(p.id);
              return (
                <div key={p.id} className="card space-y-2">
                  <div className="flex items-center justify-between">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-bold text-white ${meta.color}`}
                    >
                      {meta.short}
                    </span>
                    <StatusPill ready={p.ready} />
                  </div>
                  <p className="font-semibold">{p.label}</p>
                  <p className="break-all font-mono text-[10px] text-ink-800/60">
                    {p.binary || "(no binary)"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {latest ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold">
                Lần so sánh đa-model gần nhất · {latest.game}
              </h3>
              <p className="text-sm text-ink-800/70">
                {latest.created} · <code className="text-xs">{latest.path}</code>
              </p>
            </div>
            {latest.fen ? <MiniBoard fen={latest.fen} size={120} /> : null}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {latest.reviews.map((r) => (
              <ReviewCard key={r.provider + (r.created || "")} review={r} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
