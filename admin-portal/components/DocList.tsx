import Link from "next/link";
import type { VaultDoc } from "@/lib/vault";

export function DocList({
  docs,
  empty,
}: {
  docs: VaultDoc[];
  empty: string;
}) {
  if (!docs.length) {
    return (
      <div className="card text-sm text-ink-800/70">
        {empty}
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {docs.map((doc) => (
        <li key={doc.path} className="card">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold">{doc.title}</h3>
              <p className="mt-1 text-xs text-ink-800/50">{doc.path}</p>
              {doc.excerpt ? (
                <p className="mt-2 text-sm text-ink-800/80">{doc.excerpt}…</p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-1">
              {typeof doc.data.bloom === "string" ? (
                <span className="badge">{doc.data.bloom}</span>
              ) : null}
              {typeof doc.data.type === "string" ? (
                <span className="badge">{doc.data.type}</span>
              ) : null}
              {typeof doc.data.student_level === "string" ? (
                <span className="badge">{doc.data.student_level}</span>
              ) : null}
            </div>
          </div>
          {typeof doc.data.fen === "string" && doc.data.fen ? (
            <p className="mt-3 break-all rounded-lg bg-ink-50 p-2 font-mono text-xs">
              {doc.data.fen}
            </p>
          ) : null}
          <details className="mt-3">
            <summary className="cursor-pointer text-sm font-medium text-board-accent">
              Xem nội dung
            </summary>
            <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-50">
              {doc.body}
            </pre>
          </details>
        </li>
      ))}
    </ul>
  );
}

export function PageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-bold">{title}</h2>
      {subtitle ? (
        <p className="mt-1 text-sm text-ink-800/70">{subtitle}</p>
      ) : null}
      <p className="mt-2 text-xs">
        <Link href="/" className="text-board-accent hover:underline">
          ← Tổng quan
        </Link>
      </p>
    </div>
  );
}
