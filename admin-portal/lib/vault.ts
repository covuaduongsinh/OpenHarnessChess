import fs from "fs";
import path from "path";
import matter from "gray-matter";

export type VaultDoc = {
  slug: string;
  path: string;
  title: string;
  data: Record<string, unknown>;
  excerpt: string;
  body: string;
};

export function vaultRoot(): string {
  return (
    process.env.OHCC_VAULT ||
    process.env.OHCC_VAULT_PATH ||
    path.join(process.cwd(), "..", "vault")
  );
}

export function listMarkdown(relDir: string): VaultDoc[] {
  const dir = path.join(vaultRoot(), relDir);
  if (!fs.existsSync(dir)) return [];
  const files = walkMd(dir);
  return files
    .map((file) => readMarkdown(file))
    .filter((d): d is VaultDoc => d !== null)
    .sort((a, b) => a.title.localeCompare(b.title, "vi"));
}

export function readMarkdown(filePath: string): VaultDoc | null {
  if (!fs.existsSync(filePath) || !filePath.endsWith(".md")) return null;
  const raw = fs.readFileSync(filePath, "utf8");
  const { data, content } = matter(raw);
  const rel = path.relative(vaultRoot(), filePath).replace(/\\/g, "/");
  const title =
    (typeof data.title === "string" && data.title) ||
    firstHeading(content) ||
    path.basename(filePath, ".md");
  const excerpt = content
    .replace(/^#.*$/m, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 160);
  return {
    slug: rel.replace(/\.md$/, ""),
    path: rel,
    title,
    data: data as Record<string, unknown>,
    excerpt,
    body: content,
  };
}

export function dashboardStats() {
  const students = listMarkdown("01-students").length;
  const lessons = listMarkdown("02-lessons").length;
  const puzzles = [
    ...listMarkdown("03-puzzles/bloom-remember"),
    ...listMarkdown("03-puzzles/bloom-apply"),
    ...listMarkdown("03-puzzles/bloom-analyze"),
  ].length;
  const games = listFiles("04-games", [".pgn", ".md"]).length;
  const inbox = listMarkdown("00-inbox").length;
  return { students, lessons, puzzles, games, inbox, vault: vaultRoot() };
}

function listFiles(relDir: string, exts: string[]): string[] {
  const dir = path.join(vaultRoot(), relDir);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => exts.some((e) => f.toLowerCase().endsWith(e)))
    .map((f) => path.join(relDir, f).replace(/\\/g, "/"));
}

function walkMd(dir: string): string[] {
  const out: string[] = [];
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const st = fs.statSync(full);
    if (st.isDirectory()) out.push(...walkMd(full));
    else if (name.endsWith(".md")) out.push(full);
  }
  return out;
}

function firstHeading(md: string): string | null {
  const m = md.match(/^#\s+(.+)$/m);
  return m ? m[1].trim() : null;
}
