import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { listEngagements } from "@/lib/api";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const engagements = await listEngagements();
  const currentId = engagements[0]?.id;
  const orgName = engagements[0]?.org_name || "Hemera";

  return (
    <div className="flex min-h-screen">
      <Sidebar engagementId={currentId} orgName={orgName} />
      <div className="flex-1 flex flex-col">
        <Topbar engagements={engagements} currentId={currentId} />
        <main className="flex-1 p-6 bg-paper">{children}</main>
      </div>
    </div>
  );
}
