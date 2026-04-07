import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { listEngagements } from "@/lib/api";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let engagements: Awaited<ReturnType<typeof listEngagements>> = [];
  try {
    engagements = await listEngagements();
  } catch (e) {
    console.error("[dashboard] Failed to load engagements:", e);
  }

  const currentId = engagements[0]?.id;
  const orgName = engagements[0]?.org_name || "Hemera";

  return (
    <div className="flex min-h-screen">
      <Sidebar engagementId={currentId} orgName={orgName} />
      <div className="flex-1 flex flex-col">
        <Topbar engagements={engagements} currentId={currentId} />
        <main className="flex-1 p-6 bg-paper">{children}</main>
        <footer className="px-6 py-4 border-t border-[#E5E5E0] text-center text-[11px] text-muted">
          © 2026 Hemera · Supply Chain Carbon Intelligence · <a href="mailto:hello@hemera.co" className="text-teal hover:underline">hello@hemera.co</a>
        </footer>
      </div>
    </div>
  );
}
