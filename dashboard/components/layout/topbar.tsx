"use client";

import { UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import type { EngagementListItem } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function Topbar({
  engagements,
  currentId,
}: {
  engagements: EngagementListItem[];
  currentId?: number;
}) {
  const router = useRouter();

  return (
    <div className="bg-surface px-6 py-3 border-b border-[#E5E5E0] flex items-center justify-between">
      <div className="flex items-center gap-2 text-[13px] text-muted">
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
      </div>
      <div className="flex items-center gap-3">
        {currentId && (
          <a
            href={`${API_URL}/api/reports/${currentId}/pdf`}
            className="px-3 py-1.5 rounded-md text-xs font-semibold text-muted border border-[#E5E5E0] hover:bg-slate-tint"
          >
            ↓ PDF Report
          </a>
        )}
        <UserButton />
      </div>
    </div>
  );
}
