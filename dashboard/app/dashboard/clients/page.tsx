import { getHemeraUser } from "@/lib/auth";
import { listEngagements } from "@/lib/api";
import type { EngagementListItem } from "@/lib/types";
import { ClientQueue } from "./client-queue";

export default async function ClientsPage() {
  const user = await getHemeraUser();

  if (user?.role !== "admin") {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <h3 className="text-lg font-semibold mb-1">Admin Access Required</h3>
          <p className="text-muted text-sm">
            Contact your account manager if you need access.
          </p>
        </div>
      </div>
    );
  }

  let engagements: EngagementListItem[] = [];
  let error: string | null = null;
  try {
    engagements = await listEngagements();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load engagements";
  }

  return <ClientQueue engagements={engagements} error={error} />;
}
