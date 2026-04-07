import { getHemeraUser } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { listEngagements } from "@/lib/api";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const hemeraUser = await getHemeraUser();
  const role = hemeraUser?.role || "client";

  let engagements: Awaited<ReturnType<typeof listEngagements>> = [];
  try {
    engagements = await listEngagements();
  } catch (e) {
    console.error("[dashboard] Failed to load engagements:", e);
  }

  const currentId = engagements[0]?.id;
  const orgName = hemeraUser?.orgName || engagements[0]?.org_name || "Hemera";

  return (
    <div className="flex min-h-screen">
      <Sidebar engagementId={currentId} orgName={orgName} role={role} />
      <div className="flex-1 flex flex-col">
        <Topbar engagements={engagements} currentId={currentId} role={role} />
        <main className="flex-1 p-6 bg-paper">{children}</main>
        {role !== "admin" && (
          <footer className="px-6 py-4 border-t border-[#E5E5E0] text-center text-[11px] text-muted">
            © 2026 Hemera · Supply Chain Carbon Intelligence
          </footer>
        )}
      </div>
    </div>
  );
}
