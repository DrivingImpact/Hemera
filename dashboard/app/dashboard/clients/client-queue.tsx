"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useState } from "react";
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
    description: "QC passed — review the final report before releasing to client",
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

  // Group engagements by stage
  const stageGroups = STAGES.map((stage) => ({
    stage,
    items: engagements
      .filter((e) => stage.statuses.includes(e.status))
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || "")),
  }));

  // Also include qc_passed as "review report" since we don't have "released" status yet
  // The "completed" stage will show qc_passed items that admin has reviewed
  // For now, qc_passed goes to "Review Report"

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
/*  Engagement card with inline editing                                */
/* ------------------------------------------------------------------ */

function EngagementCard({
  eng,
  stage,
  onUpdate,
}: {
  eng: EngagementListItem;
  stage: Stage;
  onUpdate: (id: number, patch: { display_name?: string; admin_notes?: string }) => Promise<void>;
}) {
  const [editingName, setEditingName] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [nameValue, setNameValue] = useState(eng.display_name || "");
  const [notesValue, setNotesValue] = useState(eng.admin_notes || "");

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

  return (
    <div className="bg-surface rounded-xl border border-[#E5E5E0] p-5 space-y-3 hover:border-teal/30 transition-colors">
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
          </div>
          <div className="text-muted text-xs mt-0.5 flex items-center gap-3">
            <span>#{eng.id}</span>
            <span>{date}</span>
            <span>{eng.transaction_count?.toLocaleString() ?? "—"} transactions</span>
            {eng.total_co2e != null && eng.total_co2e > 0 && (
              <span className="font-medium">{eng.total_co2e.toFixed(1)} tCO2e</span>
            )}
          </div>
        </div>

        {/* Action buttons */}
        {stage.key === "processing" ? (
          <div className="flex-shrink-0 flex items-center gap-2 text-muted text-xs">
            <div className="w-4 h-4 rounded-full border-2 border-amber/30 border-t-amber animate-spin" />
            Processing
          </div>
        ) : stage.key === "review" ? (
          <div className="flex-shrink-0 flex items-center gap-2">
            <Link
              href={`/dashboard/${eng.id}/qc`}
              className="px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-90 bg-teal text-white"
            >
              {eng.qc_progress && eng.qc_progress.reviewed > 0 ? "Continue Carbon" : "Carbon Review"}
            </Link>
            <Link
              href={`/dashboard/${eng.id}/supplier-review`}
              className="px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-90 bg-[#6366F1] text-white"
            >
              Supplier Review
            </Link>
          </div>
        ) : (
          <Link
            href={stage.actionHref(eng)}
            className={`flex-shrink-0 px-5 py-2.5 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90 ${stage.actionStyle}`}
          >
            {stage.actionLabel(eng)}
          </Link>
        )}
      </div>

      {/* QC Progress bar */}
      {eng.qc_progress && eng.qc_progress.sampled > 0 && (
        <div className="border-t border-[#F0F0EB] pt-2">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
              <div
                className="h-full bg-teal rounded-full transition-all"
                style={{ width: `${(eng.qc_progress.reviewed / eng.qc_progress.sampled) * 100}%` }}
              />
            </div>
            <span className="text-[11px] text-muted tabular-nums flex-shrink-0">
              {eng.qc_progress.reviewed}/{eng.qc_progress.sampled} reviewed
            </span>
          </div>
        </div>
      )}

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
              <span className="text-[10px] text-muted">⌘+Enter to save</span>
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
