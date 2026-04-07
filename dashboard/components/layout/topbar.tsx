"use client";

import { UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import type { EngagementListItem } from "@/lib/types";

export function Topbar({
  engagements,
  currentId,
  role,
}: {
  engagements: EngagementListItem[];
  currentId?: number;
  role: string;
}) {
  const router = useRouter();

  return (
    <div className="bg-surface px-6 py-3 border-b border-[#E5E5E0] flex items-center justify-between">
      <div className="flex items-center gap-2 text-[13px] text-muted">
        {role === "admin" ? (
          <span className="text-xs font-semibold text-slate">Hemera Admin</span>
        ) : engagements.length > 0 ? (
          <>
            <span>Engagement:</span>
            <select
              className="border border-[#E5E5E0] rounded px-2 py-1 text-xs font-sans bg-[#FAFAF7]"
              value={currentId || ""}
              onChange={(e) => {
                const id = e.target.value;
                if (id) router.push(`/dashboard/${id}`);
              }}
            >
              {engagements.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.org_name} — {e.status}
                </option>
              ))}
            </select>
          </>
        ) : null}
      </div>
      <UserButton />
    </div>
  );
}
