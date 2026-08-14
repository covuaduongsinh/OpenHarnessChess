import { DocList, PageHeader } from "@/components/DocList";
import { listMarkdown } from "@/lib/vault";

export const dynamic = "force-dynamic";

export default function StudentsPage() {
  const docs = listMarkdown("01-students");
  return (
    <div>
      <PageHeader
        title="Học viên"
        subtitle="Hồ sơ memory trong vault/01-students (template student-profile)."
      />
      <DocList
        docs={docs}
        empty="Chưa có hồ sơ học viên. Tạo file từ vault/templates/student-profile.md."
      />
    </div>
  );
}
