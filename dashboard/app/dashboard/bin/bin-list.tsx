"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useState } from "react";
import type { EngagementListItem } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function BinList({
  engagements: initialEngagements,
  error,
}: {
  engagements: EngagementListItem[];
  error: string | null;
}) {
  const { getToken } = useAuth();
  const [engagements, setEngagements] = useState(initialEngagements);
  const [showEmptyConfirm, setShowEmptyConfirm] = useState(false);
  const [emptyingBin, setEmptyingBin] = useState(false);

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
    [getToken],
  );

  const restoreEngagement = useCallback(
    async (id: number) => {
      await apiFetch(`/engagements/${id}/restore`, { method: "POST" });
      setEngagements((prev) => prev.filter((e) => e.id !== id));
    },
    [apiFetch],
  );

  const permanentDelete = useCallback(
    async (id: number) => {
      await apiFetch(`/engagements/${id}/permanent`, { method: "DELETE" });
      setEngagements((prev) => prev.filter((e) => e.id !== id));
    },
    [apiFetch],
  );

  const emptyBin = useCallback(async () => {
    setEmptyingBin(true);
    try {
      await Promise.all(
        engagements.map((e) =>
          apiFetch(`/engagements/${e.id}/permanent`, { method: "DELETE" }),
        ),
      );
      setEngagements([]);
      setShowEmptyConfirm(false);
    } catch {
      // keep items that failed
    } finally {
      setEmptyingBin(false);
    }
  }, [apiFetch, engagements]);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Bin</h1>
          <p className="text-muted text-sm mt-0.5">
            {engagements.length > 0
              ? `${engagements.length} deleted engagement${engagements.length !== 1 ? "s" : ""}`
              : "No deleted engagements"}
          </p>
        </div>
        {engagements.length > 0 && (
          <button
            onClick={() => setShowEmptyConfirm(true)}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Empty bin
          </button>
        )}
      </div>

      {/* Empty bin confirmation */}
      {showEmptyConfirm && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between">
          <span className="text-sm text-red-800">
            Permanently delete all {engagements.length} engagement
            {engagements.length !== 1 ? "s" : ""}? This cannot be undone.
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={emptyBin}
              disabled={emptyingBin}
              className="px-4 py-1.5 bg-red-600 text-white text-xs font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              {emptyingBin ? "Deleting..." : "Delete all permanently"}
            </button>
            <button
              onClick={() => setShowEmptyConfirm(false)}
              className="px-3 py-1.5 text-xs text-muted hover:underline"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6 text-center">
          <p className="text-error text-sm">{error}</p>
          <p className="text-muted text-xs mt-1">
            Check that the API is running and try refreshing.
          </p>
        </div>
      )}

      {/* Engagement cards */}
      {engagements.map((eng) => (
        <BinCard
          key={eng.id}
          eng={eng}
          onRestore={restoreEngagement}
          onPermanentDelete={permanentDelete}
        />
      ))}

      {engagements.length === 0 && !error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <svg
            className="mx-auto mb-3 text-muted"
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3,6 5,6 21,6" />
            <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6" />
          </svg>
          <p className="text-muted text-sm">Bin is empty</p>
          <p className="text-muted text-xs mt-1">
            Deleted engagements will appear here.
          </p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Individual deleted engagement card                                 */
/* ------------------------------------------------------------------ */

function BinCard({
  eng,
  onRestore,
  onPermanentDelete,
}: {
  eng: EngagementListItem;
  onRestore: (id: number) => Promise<void>;
  onPermanentDelete: (id: number) => Promise<void>;
}) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const name = eng.display_name || eng.org_name;

  const uploadDate = eng.created_at
    ? new Date(eng.created_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  const deletedDate = eng.deleted_at
    ? new Date(eng.deleted_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  const handleRestore = async () => {
    setRestoring(true);
    try {
      await onRestore(eng.id);
    } catch {
      setRestoring(false);
    }
  };

  const handlePermanentDelete = async () => {
    setDeleting(true);
    try {
      await onPermanentDelete(eng.id);
    } catch {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  return (
    <div
      className={`bg-surface rounded-xl border border-[#E5E5E0] p-5 space-y-3 transition-all ${
        restoring || deleting ? "opacity-0 scale-95" : ""
      }`}
    >
      {/* Permanent delete confirmation */}
      {showDeleteConfirm && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
          <span className="text-sm text-red-800">
            Permanently delete this engagement? This cannot be undone.
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePermanentDelete}
              disabled={deleting}
              className="px-3 py-1 bg-red-600 text-white text-xs font-semibold rounded hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete forever"}
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

      {/* Card content */}
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-[15px]">{name}</h3>
          <div className="text-muted text-xs mt-1 space-y-0.5">
            {eng.deleted_by && deletedDate && (
              <p>
                Deleted by {eng.deleted_by} on {deletedDate}
              </p>
            )}
            <div className="flex items-center gap-3 flex-wrap">
              {uploadDate && <span>Uploaded {uploadDate}</span>}
              <span>
                {eng.transaction_count?.toLocaleString() ?? "0"} transactions
              </span>
              <span>#{eng.id}</span>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex-shrink-0 flex items-center gap-2">
          <button
            onClick={handleRestore}
            disabled={restoring}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-teal text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {restoring ? "Restoring..." : "Restore"}
          </button>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Delete permanently
          </button>
        </div>
      </div>
    </div>
  );
}
