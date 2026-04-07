import { redirect } from "next/navigation";
import { listEngagements } from "@/lib/api";

export default async function DashboardPage() {
  const engagements = await listEngagements();
  if (engagements.length === 0) {
    redirect("/dashboard/upload");
  }
  redirect(`/dashboard/${engagements[0].id}`);
}
