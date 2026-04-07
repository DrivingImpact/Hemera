import Link from "next/link";
import { listEngagements } from "@/lib/api";
import { UploadDropzone } from "@/components/upload/dropzone";
import { DeleteEngagement } from "@/components/upload/delete-engagement";
import type { EngagementListItem } from "@/lib/types";

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  uploaded: {
    label: "Awaiting review",
    className: "bg-amber-tint text-amber border border-amber/30",
  },
  processing: {
    label: "Processing",
    className: "bg-amber-tint text-amber border border-amber/30",
  },
  delivered: {
    label: "Ready for QC",
    className: "bg-teal-tint text-teal border border-teal/30",
  },
  qc_passed: {
    label: "Approved",
    className: "bg-[#D1FAE5] text-[#065F46] border border-[#A7F3D0]",
  },
};

export default async function UploadPage() {
  let engagements: EngagementListItem[] = [];
  try {
    engagements = await listEngagements();
  } catch {
    // silently fall through — show upload form without engagement list
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Upload Spend Data</h1>
        <p className="text-muted text-sm mt-0.5">
          Upload a CSV or Excel file to create a new engagement. We&apos;ll classify
          emissions and match suppliers automatically.
        </p>
      </div>

      <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6">
        <UploadDropzone />
      </div>

      {engagements.length > 0 && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#E5E5E0]">
            <h4 className="text-xs font-semibold uppercase tracking-[0.5px]">Your Uploads</h4>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E5E0] bg-paper">
                <th className="text-left px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
                  Engagement
                </th>
                <th className="text-right px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
                  Transactions
                </th>
                <th className="text-left px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
                  Status
                </th>
                <th className="text-right px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
                  View
                </th>
                <th className="text-right px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {engagements.map((eng: EngagementListItem) => {
                const badge = STATUS_BADGE[eng.status] ?? {
                  label: eng.status,
                  className: "bg-paper text-muted border border-[#E5E5E0]",
                };
                return (
                  <tr key={eng.id} className="border-b border-[#F0F0EB] last:border-0 hover:bg-paper transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-medium">{eng.org_name}</div>
                      <div className="text-[11px] text-muted">#{eng.id}</div>
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-muted">
                      {eng.transaction_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${badge.className}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      {eng.status === "qc_passed" ? (
                        <Link
                          href={`/dashboard/${eng.id}`}
                          className="text-teal text-xs font-medium hover:underline"
                        >
                          View →
                        </Link>
                      ) : (
                        <span className="text-[#CBCBC5] text-xs">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {eng.status !== "qc_passed" && (
                        <DeleteEngagement engagementId={eng.id} />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
}
