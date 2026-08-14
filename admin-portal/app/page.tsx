import Link from "next/link";
import { dashboardStats } from "@/lib/vault";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  const stats = dashboardStats();
  const cards = [
    { label: "Phân tích cờ (heuristic)", value: stats.puzzles, href: "/analysis", hint: "Bloom pipeline MIT" },
    { label: "LLM Coach", value: 4, href: "/llm", hint: "Antigravity · Claude · Grok · Codex" },
    { label: "Học viên", value: stats.students, href: "/students" },
    { label: "Giáo án", value: stats.lessons, href: "/lessons" },
    { label: "Bài tập Bloom", value: stats.puzzles, href: "/puzzles" },
    { label: "Ván / PGN", value: stats.games, href: "/games" },
    { label: "Inbox ảnh", value: stats.inbox, href: "/inbox" },
  ];

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-2xl font-bold">Tổng quan vault</h2>
        <p className="mt-1 text-sm text-ink-800/70">
          Nguồn: <code className="rounded bg-ink-100 px-1">{stats.vault}</code>
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <Link key={c.href + c.label} href={c.href} className="card transition hover:shadow-md">
            <p className="text-sm text-ink-800/70">{c.label}</p>
            <p className="mt-2 text-3xl font-bold text-board-accent">{c.value}</p>
            {"hint" in c && c.hint ? (
              <p className="mt-1 text-xs text-board-accent/80">{c.hint}</p>
            ) : null}
          </Link>
        ))}
      </section>

      <section className="card space-y-3">
        <h3 className="font-semibold">Pipeline OHCC</h3>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-ink-800/90">
          <li>PGN → <code>python -m ohcc.scaffolding --pgn … --vault vault</code></li>
          <li>Eval drops (tuỳ chọn): thêm <code>--arasan</code></li>
          <li>Xem kết quả phân tích tại <Link href="/analysis" className="text-board-accent underline">/analysis</Link></li>
          <li>Ảnh bàn cờ: vision-board-mcp → <code>vault/00-inbox</code></li>
          <li>Coach: Thầy Tường (Socratic + Bloom)</li>
        </ol>
      </section>
    </div>
  );
}
