"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useRef, useState } from "react";
import type { EngagementListItem } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Pipeline stages                                                    */
/* ------------------------------------------------------------------ */

interface Stage {
  key: string;
  label: string;
  description: string;
  statuses: string[];
  actionLabel: (eng: EngagementListItem) => string;
  actionHref: (eng: EngagementListItem) => string;
  actionStyle: string;
}

const STAGES: Stage[] = [
  {
    key: "process",
    label: "Process",
    description: "Classify transactions and calculate carbon footprint",
    statuses: ["uploaded"],
    actionLabel: (eng) => `Process ${eng.transaction_count?.toLocaleString() ?? ""} txns`,
    actionHref: (eng) => `/dashboard/${eng.id}/qc`,
    actionStyle: "bg-slate text-white",
  },
  {
    key: "processing",
    label: "Processing",
    description: "Classification and calculation in progress",
    statuses: ["processing"],
    actionLabel: () => "Processing...",
    actionHref: (eng) => `/dashboard/${eng.id}/qc`,
    actionStyle: "bg-paper text-muted border border-[#E5E5E0]",
  },
  {
    key: "review",
    label: "Review",
    description: "Carbon classification QC and supplier claims verification",
    statuses: ["delivered"],
    actionLabel: (eng) => eng.qc_progress && eng.qc_progress.reviewed > 0 ? "Continue Carbon Review" : "Start Carbon Review",
    actionHref: (eng) => `/dashboard/${eng.id}/qc`,
    actionStyle: "bg-teal text-white",
  },
  {
    key: "review_report",
    label: "Review Report",
    description: "QC passed — review the carbon report and curate HemeraScope before releasing to client",
    statuses: ["qc_passed"],
    actionLabel: () => "Review Report",
    actionHref: (eng) => `/dashboard/${eng.id}`,
    actionStyle: "bg-[#6366F1] text-white",
  },
  {
    key: "completed",
    label: "Completed",
    description: "Approved and delivered to client",
    statuses: ["released"],
    actionLabel: () => "View",
    actionHref: (eng) => `/dashboard/${eng.id}`,
    actionStyle: "border border-[#E5E5E0] text-muted",
  },
];

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function ClientQueue({
  engagements: initialEngagements,
  error,
}: {
  engagements: EngagementListItem[];
  error: string | null;
}) {
  const { getToken } = useAuth();
  const [engagements, setEngagements] = useState(initialEngagements);

  const apiFetch = useCallback(
    async (path: string, options?: RequestInit) => {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...options?.headers,
        },
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      return res.json();
    },
    [getToken]
  );

  const updateEngagement = useCallback(
    async (id: number, patch: { display_name?: string; admin_notes?: string }) => {
      await apiFetch(`/engagements/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      setEngagements((prev) =>
        prev.map((e) => (e.id === id ? { ...e, ...patch } : e))
      );
    },
    [apiFetch]
  );

  const deleteEngagement = useCallback(
    async (id: number) => {
      await apiFetch(`/engagements/${id}`, { method: "DELETE" });
      setEngagements((prev) => prev.filter((e) => e.id !== id));
    },
    [apiFetch]
  );

  // Group engagements by stage
  const stageGroups = STAGES.map((stage) => ({
    stage,
    items: engagements
      .filter((e) => stage.statuses.includes(e.status))
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || "")),
  }));

  const totalAction = stageGroups
    .filter((g) => ["process", "carbon_review"].includes(g.stage.key))
    .reduce((sum, g) => sum + g.items.length, 0);

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Client Queue</h1>
        <p className="text-muted text-sm mt-0.5">
          {totalAction > 0
            ? `${totalAction} engagement${totalAction !== 1 ? "s" : ""} need${totalAction === 1 ? "s" : ""} your attention`
            : "All caught up"}
        </p>
      </div>

      {error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6 text-center">
          <p className="text-error text-sm">{error}</p>
          <p className="text-muted text-xs mt-1">Check that the API is running and try refreshing.</p>
        </div>
      )}

      {/* Pipeline stages */}
      {stageGroups.map(({ stage, items }) => {
        if (items.length === 0) return null;
        return (
          <div key={stage.key} className="space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">{stage.label}</h2>
              <span className="text-[10px] bg-paper text-muted px-1.5 py-0.5 rounded-full font-semibold">{items.length}</span>
            </div>
            <p className="text-[11px] text-muted -mt-1">{stage.description}</p>
            {items.map((eng) => (
              <EngagementCard
                key={eng.id}
                eng={eng}
                stage={stage}
                onUpdate={updateEngagement}
                onDelete={deleteEngagement}
              />
            ))}
          </div>
        );
      })}

      {engagements.length === 0 && !error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm">No engagements yet. Clients need to upload spend data first.</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Engagement card with inline editing, delete, and info dropdown     */
/* ------------------------------------------------------------------ */

function EngagementCard({
  eng,
  stage,
  onUpdate,
  onDelete,
}: {
  eng: EngagementListItem;
  stage: Stage;
  onUpdate: (id: number, patch: { display_name?: string; admin_notes?: string }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [editingName, setEditingName] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [nameValue, setNameValue] = useState(eng.display_name || "");
  const [notesValue, setNotesValue] = useState(eng.admin_notes || "");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const infoRef = useRef<HTMLDivElement>(null);

  const date = eng.created_at
    ? new Date(eng.created_at).toLocaleDateString("en-GB", {
        day: "numeric", month: "short", year: "numeric",
      })
    : "—";

  const uploaderLabel = eng.display_name || eng.uploaded_by_email || eng.org_name;

  const saveName = async () => {
    await onUpdate(eng.id, { display_name: nameValue });
    setEditingName(false);
  };

  const saveNotes = async () => {
    await onUpdate(eng.id, { admin_notes: notesValue });
    setEditingNotes(false);
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(eng.id);
    } catch {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  // Close info popover on click outside
  useEffect(() => {
    if (!showInfo) return;
    const handler = (e: MouseEvent) => {
      if (infoRef.current && !infoRef.current.contains(e.target as Node)) {
        setShowInfo(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showInfo]);

  // Close info on Escape
  useEffect(() => {
    if (!showInfo) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowInfo(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [showInfo]);

  return (
    <div className={`bg-surface rounded-xl border border-[#E5E5E0] p-5 space-y-3 hover:border-teal/30 transition-all ${deleting ? "opacity-0 scale-95" : ""}`}>
      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
          <span className="text-sm text-red-800">Delete this engagement? It will be moved to the bin.</span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="px-3 py-1 bg-red-600 text-white text-xs font-semibold rounded hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="px-3 py-1 text-xs text-muted hover:underline"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Top row */}
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          {/* Uploader name — click to edit */}
          <div className="flex items-center gap-2">
            {editingName ? (
              <div className="flex items-center gap-1.5">
                <input
                  autoFocus
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") saveName(); if (e.key === "Escape") setEditingName(false); }}
                  className="border border-teal rounded px-2 py-0.5 text-[15px] font-semibold w-48 outline-none"
                  placeholder="e.g. John (SU)"
                />
                <button onClick={saveName} className="text-teal text-xs font-semibold hover:underline">Save</button>
                <button onClick={() => setEditingName(false)} className="text-muted text-xs hover:underline">Cancel</button>
              </div>
            ) : (
              <button
                onClick={() => { setNameValue(eng.display_name || ""); setEditingName(true); }}
                className="font-semibold text-[15px] hover:text-teal transition-colors text-left"
                title="Click to rename"
              >
                {uploaderLabel}
              </button>
            )}
            {eng.display_name && eng.org_name && eng.display_name !== eng.org_name && (
              <span className="text-[10px] text-muted bg-paper px-1.5 py-0.5 rounded">{eng.org_name}</span>
            )}

            {/* Info dropdown toggle */}
            <div className="relative" ref={infoRef}>
              <button
                onClick={() => setShowInfo(!showInfo)}
                className="text-muted hover:text-teal transition-colors p-0.5"
                title="Engagement details"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4" />
                  <path d="M12 8h.01" />
                </svg>
              </button>

              {/* Info popover */}
              {showInfo && (
                <div className="absolute left-0 top-7 z-50 bg-white border border-[#E5E5E0] rounded-lg shadow-lg p-4 w-72 space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-[0.5px] text-muted mb-2">Engagement Details</div>
                  <InfoRow label="Uploaded by" value={eng.uploaded_by_email} />
                  <InfoRow label="Organisation" value={eng.org_name} />
                  {eng.contact_email && <InfoRow label="Contact" value={eng.contact_email} />}
                  <InfoRow label="Upload date" value={date} />
                  {eng.upload_filename && <InfoRow label="File" value={eng.upload_filename} />}
                  <InfoRow label="Transactions" value={eng.transaction_count?.toLocaleString() ?? "—"} />
                  {eng.total_co2e != null && eng.total_co2e > 0 && (
                    <InfoRow label="Total CO2e" value={`${eng.total_co2e.toFixed(1)} tCO2e`} />
                  )}
                  <InfoRow label="Status" value={eng.status} />
                </div>
              )}
            </div>
          </div>
          <div className="text-muted text-xs mt-0.5 flex items-center gap-3 flex-wrap">
            <span>#{eng.id}</span>
            <span>{date}</span>
            <span>{eng.transaction_count?.toLocaleString() ?? "—"} transactions</span>
            {eng.total_co2e != null && eng.total_co2e > 0 && (
              <span className="font-medium">{eng.total_co2e.toFixed(1)} tCO2e</span>
            )}
            {eng.uploaded_by_email && (
              <span
                className="text-[10px] bg-paper px-1.5 py-0.5 rounded font-medium"
                title="Person who uploaded this engagement"
              >
                by {eng.uploaded_by_email}
              </span>
            )}
          </div>
        </div>

        {/* Action buttons + delete */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {/* Delete button */}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="p-1.5 text-muted hover:text-red-500 transition-colors rounded hover:bg-red-50"
            title="Delete engagement"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3,6 5,6 21,6" />
              <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6" />
            </svg>
          </button>

          {stage.key === "processing" ? (
            <div className="flex items-center gap-2 text-muted text-xs">
              <div className="w-4 h-4 rounded-full border-2 border-amber/30 border-t-amber animate-spin" />
              Processing
            </div>
          ) : stage.key === "review" ? (
            <>
              <Link
                href={`/dashboard/${eng.id}/qc`}
                className="px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-90 bg-teal text-white"
              >
                {eng.qc_progress && eng.qc_progress.reviewed > 0 ? "Continue Carbon" : "Carbon Review"}
              </Link>
              <Link
                href={`/dashboard/${eng.id}/hemerascope`}
                className="px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-90 bg-[#6366F1] text-white"
              >
                Supplier Review
              </Link>
            </>
          ) : (
            <Link
              href={stage.actionHref(eng)}
              className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90 ${stage.actionStyle}`}
            >
              {stage.actionLabel(eng)}
            </Link>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <EngagementProgress eng={eng} />

      {/* Notes */}
      <div className="border-t border-[#F0F0EB] pt-2">
        {editingNotes ? (
          <div className="space-y-1.5">
            <textarea
              autoFocus
              value={notesValue}
              onChange={(e) => setNotesValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && e.metaKey) saveNotes(); if (e.key === "Escape") setEditingNotes(false); }}
              className="w-full border border-teal rounded-lg px-3 py-2 text-xs outline-none resize-none"
              rows={2}
              placeholder="Add notes about this engagement..."
            />
            <div className="flex items-center gap-2">
              <button onClick={saveNotes} className="text-teal text-[11px] font-semibold hover:underline">Save</button>
              <button onClick={() => setEditingNotes(false)} className="text-muted text-[11px] hover:underline">Cancel</button>
              <span className="text-[10px] text-muted">Cmd+Enter to save</span>
            </div>
          </div>
        ) : (
          <button
            onClick={() => { setNotesValue(eng.admin_notes || ""); setEditingNotes(true); }}
            className="text-xs text-left w-full hover:text-teal transition-colors"
          >
            {eng.admin_notes ? (
              <span className="text-slate">{eng.admin_notes}</span>
            ) : (
              <span className="text-muted italic">Add notes...</span>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Info row for the ownership popover                                 */
/* ------------------------------------------------------------------ */

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted w-20 flex-shrink-0 pt-0.5">{label}</span>
      <span className="text-xs text-slate break-all">{value}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Progress bar per engagement                                        */
/* ------------------------------------------------------------------ */

function EngagementProgress({ eng }: { eng: EngagementListItem }) {
  if (eng.status === "delivered") {
    // Two progress bars for carbon + supplier review
    const qc = eng.qc_progress;
    const carbonPct = qc && qc.sampled > 0 ? Math.round((qc.reviewed / qc.sampled) * 100) : 0;
    const carbonLabel = qc && qc.sampled > 0 ? `${qc.reviewed}/${qc.sampled}` : "Not started";

    const sp = eng.supplier_progress;
    const supplierPct = sp && sp.total > 0 ? Math.round((sp.reviewed / sp.total) * 100) : 0;
    const supplierLabel = sp && sp.total > 0 ? `${sp.reviewed}/${sp.total}` : "Not started";

    return (
      <div className="border-t border-[#F0F0EB] pt-2 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted w-20 flex-shrink-0">Carbon</span>
          <div className="flex-1 h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
            <div className="h-full bg-teal rounded-full transition-all duration-500" style={{ width: `${Math.max(carbonPct, 2)}%` }} />
          </div>
          <span className="text-[10px] text-muted flex-shrink-0 tabular-nums w-20 text-right">{carbonLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted w-20 flex-shrink-0">Supplier</span>
          <div className="flex-1 h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
            <div className="h-full bg-[#6366F1] rounded-full transition-all duration-500" style={{ width: `${Math.max(supplierPct, 2)}%` }} />
          </div>
          <span className="text-[10px] text-muted flex-shrink-0 tabular-nums w-20 text-right">{supplierLabel}</span>
        </div>
      </div>
    );
  }

  // Single progress bar for other stages
  let pct = 0;
  let label = "";

  if (eng.status === "uploaded") { pct = 0; label = "Awaiting processing"; }
  else if (eng.status === "processing") { pct = 15; label = "Processing"; }
  else if (eng.status === "qc_passed") { pct = 90; label = "QC passed — review report"; }
  else if (eng.status === "released") { pct = 100; label = "Complete"; }

  const color = pct === 100 ? "bg-[#065F46]" : pct > 0 ? "bg-amber" : "bg-[#E5E5E0]";

  return (
    <div className="border-t border-[#F0F0EB] pt-2">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.max(pct, 2)}%` }} />
        </div>
        <span className="text-[10px] text-muted flex-shrink-0 tabular-nums">{label}</span>
      </div>
    </div>
  );
}
