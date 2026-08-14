import { DocList, PageHeader } from "@/components/DocList";
import { listMarkdown } from "@/lib/vault";

export const dynamic = "force-dynamic";

export default function PuzzlesPage() {
  const remember = listMarkdown("03-puzzles/bloom-remember");
  const apply = listMarkdown("03-puzzles/bloom-apply");
  const analyze = listMarkdown("03-puzzles/bloom-analyze");

  return (
    <div className="space-y-10">
      <PageHeader
        title="Bài tập Bloom"
        subtitle="Sinh bởi ScaffoldingPuzzleBuilder → vault/03-puzzles/bloom-*."
      />
      <section>
        <h3 className="mb-3 text-lg font-semibold">Nhận biết (Remember)</h3>
        <DocList docs={remember} empty="Chưa có puzzle remember." />
      </section>
      <section>
        <h3 className="mb-3 text-lg font-semibold">Áp dụng (Apply)</h3>
        <DocList docs={apply} empty="Chưa có puzzle apply." />
      </section>
      <section>
        <h3 className="mb-3 text-lg font-semibold">Phân tích (Analyze)</h3>
        <DocList docs={analyze} empty="Chưa có puzzle analyze." />
      </section>
    </div>
  );
}
