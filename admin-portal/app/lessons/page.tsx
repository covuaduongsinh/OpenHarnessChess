import { DocList, PageHeader } from "@/components/DocList";
import { listMarkdown } from "@/lib/vault";

export const dynamic = "force-dynamic";

export default function LessonsPage() {
  const docs = listMarkdown("02-lessons");
  return (
    <div>
      <PageHeader
        title="Giáo án"
        subtitle="vault/02-lessons — giáo án theo buổi."
      />
      <DocList
        docs={docs}
        empty="Chưa có giáo án. Dùng vault/templates/lesson-plan.md."
      />
    </div>
  );
}
