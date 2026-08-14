import { DocList, PageHeader } from "@/components/DocList";
import { listMarkdown } from "@/lib/vault";

export const dynamic = "force-dynamic";

export default function InboxPage() {
  const docs = listMarkdown("00-inbox");
  return (
    <div>
      <PageHeader
        title="Inbox ảnh bàn cờ"
        subtitle="vision-board-mcp ghi review notes vào vault/00-inbox."
      />
      <DocList
        docs={docs}
        empty="Inbox trống. Gửi ảnh qua vision-board-mcp (analyze_board_image_tool)."
      />
    </div>
  );
}
