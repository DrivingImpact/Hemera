import { redirect } from "next/navigation";
import { listEngagements } from "@/lib/api";

export default async function DashboardPage() {
  let engagements: Awaited<ReturnType<typeof listEngagements>> = [];
  try {
    engagements = await listEngagements();
  } catch (e) {
    console.error("[dashboard] Failed to load engagements:", e);
  }

  if (engagements.length === 0) {
    redirect("/dashboard/upload");
  }
  redirect(`/dashboard/${engagements[0].id}`);
}
