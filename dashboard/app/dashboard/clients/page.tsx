import Link from "next/link";
import { getHemeraUser } from "@/lib/auth";
import { listEngagements } from "@/lib/api";
import type { EngagementListItem } from "@/lib/types";

const STATUS_CONFIG: Record<string, {
  label: string;
  className: string;
  action: string | null;
  actionLabel: string;
  priority: number;
}> = {
  uploaded: {
    label: "Needs Processing",
    className: "bg-amber-tint text-amber border border-amber/30",
    action: "/qc",
    actionLabel: "Process",
    priority: 1,
  },
  processing: {
    label: "Processing",
    className: "bg-amber-tint text-amber border border-amber/30",
    action: null,
    actionLabel: "",
    priority: 2,
  },
  delivered: {
    label: "Needs QC Review",
    className: "bg-teal-tint text-teal border border-teal/30",
    action: "/qc",
    actionLabel: "Start Review",
    priority: 0, // highest priority — review waiting
  },
  qc_passed: {
    label: "Approved",
    className: "bg-[#D1FAE5] text-[#065F46] border border-[#A7F3D0]",
    action: "",
    actionLabel: "View Report",
    priority: 3,
  },
};

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

  // Sort: needs review first, then needs processing, then processing, then approved
  const sorted = [...engagements].sort((a, b) => {
    const pa = STATUS_CONFIG[a.status]?.priority ?? 99;
    const pb = STATUS_CONFIG[b.status]?.priority ?? 99;
    if (pa !== pb) return pa - pb;
    // Within same priority, newest first
    return (b.created_at || "").localeCompare(a.created_at || "");
  });

  const needsAction = sorted.filter((e) => e.status === "delivered" || e.status === "uploaded");
  const inProgress = sorted.filter((e) => e.status === "processing");
  const completed = sorted.filter((e) => e.status === "qc_passed");

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Client Queue</h1>
        <p className="text-muted text-sm mt-0.5">
          {needsAction.length > 0
            ? `${needsAction.length} engagement${needsAction.length !== 1 ? "s" : ""} need${needsAction.length === 1 ? "s" : ""} your attention`
            : "All caught up"}
        </p>
      </div>

      {error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6 text-center">
          <p className="text-error text-sm">{error}</p>
          <p className="text-muted text-xs mt-1">Check that the API is running and try refreshing.</p>
        </div>
      )}

      {/* Needs Action */}
      {needsAction.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">Action Required</h2>
          {needsAction.map((eng) => (
            <EngagementCard key={eng.id} eng={eng} />
          ))}
        </div>
      )}

      {/* In Progress */}
      {inProgress.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">In Progress</h2>
          {inProgress.map((eng) => (
            <EngagementCard key={eng.id} eng={eng} />
          ))}
        </div>
      )}

      {/* Completed */}
      {completed.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">Completed</h2>
          {completed.map((eng) => (
            <EngagementCard key={eng.id} eng={eng} />
          ))}
        </div>
      )}

      {engagements.length === 0 && !error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm">No engagements yet. Clients need to upload spend data first.</p>
        </div>
      )}
    </div>
  );
}

function EngagementCard({ eng }: { eng: EngagementListItem }) {
  const config = STATUS_CONFIG[eng.status] ?? {
    label: eng.status,
    className: "bg-paper text-muted border border-[#E5E5E0]",
    action: null,
    actionLabel: "",
    priority: 99,
  };

  const date = eng.created_at
    ? new Date(eng.created_at).toLocaleDateString("en-GB", {
        day: "numeric", month: "short", year: "numeric",
      })
    : "—";

  return (
    <div className="bg-surface rounded-xl border border-[#E5E5E0] p-5 flex items-center gap-5 hover:border-teal/30 transition-colors">
      {/* Left: org info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5">
          <div className="font-semibold text-[15px]">{eng.org_name}</div>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${config.className}`}>
            {config.label}
          </span>
        </div>
        <div className="text-muted text-xs mt-1 flex items-center gap-3">
          <span>#{eng.id}</span>
          <span>{date}</span>
          <span>{eng.transaction_count?.toLocaleString() ?? "—"} transactions</span>
          {eng.total_co2e != null && eng.total_co2e > 0 && (
            <span>{eng.total_co2e.toFixed(1)} tCO2e</span>
          )}
        </div>
      </div>

      {/* Right: action button */}
      {config.action !== null ? (
        <Link
          href={`/dashboard/${eng.id}${config.action}`}
          className={`flex-shrink-0 px-5 py-2.5 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90 ${
            eng.status === "delivered"
              ? "bg-teal text-white"
              : eng.status === "uploaded"
              ? "bg-slate text-white"
              : "border border-[#E5E5E0] text-muted"
          }`}
        >
          {config.actionLabel}
        </Link>
      ) : (
        <div className="flex-shrink-0 flex items-center gap-2 text-muted text-xs">
          <div className="w-4 h-4 rounded-full border-2 border-amber/30 border-t-amber animate-spin" />
          Processing
        </div>
      )}
    </div>
  );
}
