import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "OHCC Admin — CLB Cờ vua Dương Sinh",
  description: "OpenHarness Chess Coaching admin portal (MIT)",
};

const nav = [
  { href: "/", label: "Tổng quan" },
  { href: "/analysis", label: "Phân tích cờ" },
  { href: "/llm", label: "LLM Coach" },
  { href: "/students", label: "Học viên" },
  { href: "/lessons", label: "Giáo án" },
  { href: "/puzzles", label: "Bài tập" },
  { href: "/games", label: "Ván cờ" },
  { href: "/inbox", label: "Inbox ảnh" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-ink-100 bg-white">
            <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-board-accent">
                  OHCC · MIT
                </p>
                <h1 className="text-lg font-bold text-ink-900">
                  CLB Cờ vua Dương Sinh — Admin
                </h1>
                <p className="text-sm text-ink-800/70">
                  Thầy Tường · Socratic · Bloom scaffolding
                </p>
              </div>
              <nav className="flex flex-wrap gap-2">
                {nav.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded-full px-3 py-1.5 text-sm font-medium text-ink-800 hover:bg-ink-100"
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <footer className="border-t border-ink-100 py-6 text-center text-xs text-ink-800/60">
            OpenHarness Chess Coaching · Arasan (MIT) only · No Stockfish/Maia
          </footer>
        </div>
      </body>
    </html>
  );
}
