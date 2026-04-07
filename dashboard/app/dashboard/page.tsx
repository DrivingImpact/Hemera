import { redirect } from "next/navigation";
import { getHemeraUser } from "@/lib/auth";
import { listEngagements } from "@/lib/api";

export default async function DashboardPage() {
  const user = await getHemeraUser();

  if (user?.role === "admin") {
    redirect("/dashboard/clients");
  }

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
