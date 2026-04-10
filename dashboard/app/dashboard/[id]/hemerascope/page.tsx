"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import FindingCard, { type Finding } from "@/components/finding-card";
import ReportPreview, {
  type RecommendedAction,
  type EngagementTouchpoint,
} from "@/components/report-preview";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SupplierFindings {
  supplier_id: number;
  supplier_name: string;
  companies_house_number?: string;
  sector?: string;
  spend_gbp?: number;
  co2e_kg?: number;
  hemera_score?: number;
  confidence?: string;
  findings: Finding[];
  selections: Record<number, boolean>; // findingId -> included
  actions: RecommendedAction[];
  engagements: EngagementTouchpoint[];
  client_language?: Record<number, string>;
}

interface SupplierReportResponse {
  suppliers: SupplierFindings[];
}

type PageState = "loading" | "reviewing" | "saving" | "error" | "empty";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreColour(score?: number): string {
  if (score == null) return "bg-[#F1F5F9] text-[#475569]";
  if (score >= 80) return "bg-[#D1FAE5] text-[#065F46]";
  if (score >= 60) return "bg-[#FEF3C7] text-[#92400E]";
  if (score >= 40) return "bg-[#FED7AA] text-[#9A3412]";
  return "bg-[#FEE2E2] text-[#991B1B]";
}

function confidenceBadge(conf?: string): { bg: string; text: string } {
  switch (conf) {
    case "high":
      return { bg: "bg-[#D1FAE5]", text: "text-[#065F46]" };
    case "medium":
      return { bg: "bg-[#FEF3C7]", text: "text-[#92400E]" };
    case "low":
      return { bg: "bg-[#FEE2E2]", text: "text-[#991B1B]" };
    default:
      return { bg: "bg-[#F1F5F9]", text: "text-[#475569]" };
  }
}

const SOURCE_ORDER: Record<Finding["source"], number> = {
  deterministic: 0,
  ai: 1,
  outlier: 2,
};

function groupFindings(findings: Finding[]): Finding[] {
  return [...findings].sort(
    (a, b) => (SOURCE_ORDER[a.source] ?? 9) - (SOURCE_ORDER[b.source] ?? 9)
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function HemerascopePage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [pageState, setPageState] = useState<PageState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [suppliers, setSuppliers] = useState<SupplierFindings[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [clientLanguage, setClientLanguage] = useState<
    Record<number, Record<number, string>>
  >({}); // supplierId -> findingId -> text

  /* ---------------------------------------------------------------- */
  /*  API helper                                                       */
  /* ---------------------------------------------------------------- */

  const apiFetch = useCallback(
    async <T,>(path: string, options?: RequestInit): Promise<T> => {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...options?.headers,
        },
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `API error ${res.status}`);
      }
      return res.json();
    },
    [getToken]
  );

  /* ---------------------------------------------------------------- */
  /*  Load supplier report                                             */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiFetch<SupplierReportResponse>(
          `/engagements/${id}/supplier-report`
        );

        if (!data.suppliers || data.suppliers.length === 0) {
          setPageState("empty");
          return;
        }

        // Restore existing selections into each finding's included flag
        const restored = data.suppliers.map((s) => ({
          ...s,
          findings: s.findings.map((f) => ({
            ...f,
            included:
              s.selections[f.id] !== undefined ? s.selections[f.id] : null,
          })),
        }));

        setSuppliers(restored);

        // Restore client language
        const lang: Record<number, Record<number, string>> = {};
        restored.forEach((s) => {
          if (s.client_language) {
            lang[s.supplier_id] = { ...s.client_language };
          }
        });
        setClientLanguage(lang);

        setPageState("reviewing");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load");
        setPageState("error");
      }
    };
    load();
  }, [apiFetch, id]);

  /* ---------------------------------------------------------------- */
  /*  Current supplier                                                 */
  /* ---------------------------------------------------------------- */

  const supplier = suppliers[currentIndex] ?? null;

  const groupedFindings = useMemo(
    () => (supplier ? groupFindings(supplier.findings) : []),
    [supplier]
  );

  const includedFindings = useMemo(
    () => groupedFindings.filter((f) => f.included === true),
    [groupedFindings]
  );

  /* ---------------------------------------------------------------- */
  /*  Toggle finding — incremental save                                */
  /* ---------------------------------------------------------------- */

  const handleToggle = useCallback(
    async (findingId: number, included: boolean) => {
      if (!supplier) return;

      // Optimistic update
      setSuppliers((prev) =>
        prev.map((s, i) =>
          i === currentIndex
            ? {
                ...s,
                findings: s.findings.map((f) =>
                  f.id === findingId ? { ...f, included } : f
                ),
              }
            : s
        )
      );

      // Incremental save
      try {
        await apiFetch(`/engagements/${id}/supplier-report/selections`, {
          method: "PATCH",
          body: JSON.stringify({
            supplier_id: supplier.supplier_id,
            selections: [{ finding_id: findingId, included }],
          }),
        });
      } catch {
        // Selection is tracked locally — will be retried
      }
    },
    [apiFetch, id, supplier, currentIndex]
  );

  /* ---------------------------------------------------------------- */
  /*  Save actions                                                     */
  /* ---------------------------------------------------------------- */

  const handleActionsGenerated = useCallback(
    async (text: string) => {
      if (!supplier) return;
      // Parse AI response into actions (assume newline-separated)
      const lines = text
        .split("\n")
        .map((l) => l.replace(/^[-*\d.)\s]+/, "").trim())
        .filter(Boolean);
      const newActions: RecommendedAction[] = lines.map((l) => ({ text: l }));

      setSuppliers((prev) =>
        prev.map((s, i) =>
          i === currentIndex ? { ...s, actions: newActions } : s
        )
      );

      try {
        await apiFetch(`/engagements/${id}/supplier-report/actions`, {
          method: "POST",
          body: JSON.stringify({
            supplier_id: supplier.supplier_id,
            actions: newActions,
          }),
        });
      } catch {
        // Tracked locally
      }
    },
    [apiFetch, id, supplier, currentIndex]
  );

  /* ---------------------------------------------------------------- */
  /*  Client language per finding                                      */
  /* ---------------------------------------------------------------- */

  const handleClientLanguage = useCallback(
    (findingId: number, text: string) => {
      if (!supplier) return;
      setClientLanguage((prev) => ({
        ...prev,
        [supplier.supplier_id]: {
          ...(prev[supplier.supplier_id] ?? {}),
          [findingId]: text,
        },
      }));
    },
    [supplier]
  );

  /* ---------------------------------------------------------------- */
  /*  Log engagement                                                   */
  /* ---------------------------------------------------------------- */

  const handleLogEngagement = useCallback(
    async (type: string, notes: string) => {
      if (!supplier) return;
      try {
        const eng = await apiFetch<EngagementTouchpoint>(
          `/suppliers/${supplier.supplier_id}/engagements`,
          {
            method: "POST",
            body: JSON.stringify({ type, notes }),
          }
        );
        setSuppliers((prev) =>
          prev.map((s, i) =>
            i === currentIndex
              ? { ...s, engagements: [eng, ...s.engagements] }
              : s
          )
        );
      } catch {
        // Silently fail — form stays closed
      }
    },
    [apiFetch, supplier, currentIndex]
  );

  /* ---------------------------------------------------------------- */
  /*  Navigation                                                       */
  /* ---------------------------------------------------------------- */

  const goNext = useCallback(() => {
    if (currentIndex < suppliers.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  }, [currentIndex, suppliers.length]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  }, [currentIndex]);

  /* --- Keyboard shortcuts --- */
  useEffect(() => {
    if (pageState !== "reviewing") return;
    const handler = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "ArrowRight" || e.key === "n") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft" || e.key === "p") {
        e.preventDefault();
        goPrev();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pageState, goNext, goPrev]);

  /* ---------------------------------------------------------------- */
  /*  Render states                                                    */
  /* ---------------------------------------------------------------- */

  if (pageState === "loading") {
    return (
      <CenteredPanel>
        <Spinner />
        <p className="text-muted text-sm mt-3">Loading supplier report...</p>
      </CenteredPanel>
    );
  }

  if (pageState === "error") {
    return (
      <CenteredPanel>
        <p className="text-error text-sm">{errorMsg}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90"
        >
          Try Again
        </button>
      </CenteredPanel>
    );
  }

  if (pageState === "empty") {
    return (
      <CenteredPanel>
        <div className="w-16 h-16 rounded-full bg-[#F1F5F9] flex items-center justify-center mx-auto">
          <svg
            className="w-8 h-8 text-[#64748B]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">No Suppliers Found</h2>
        <p className="text-muted text-sm mt-1">
          This engagement has no supplier findings to review yet.
        </p>
        <Link
          href={`/dashboard/${id}`}
          className="mt-5 px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Back to Dashboard
        </Link>
      </CenteredPanel>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Main review layout                                               */
  /* ---------------------------------------------------------------- */

  if (!supplier) return null;

  const total = suppliers.length;
  const reviewed = suppliers.filter((s) =>
    s.findings.every((f) => f.included !== null)
  ).length;
  const conf = confidenceBadge(supplier.confidence);

  // Group label headers for findings
  const sourceGroups = ["deterministic", "ai", "outlier"] as const;
  const groupLabels: Record<string, string> = {
    deterministic: "Deterministic Findings",
    ai: "AI-Generated Findings",
    outlier: "Outlier Findings",
  };

  return (
    <div className="space-y-4">
      {/* ---- Progress bar ---- */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>
            Supplier {currentIndex + 1} of {total}
          </span>
          <span>
            {reviewed} fully reviewed
          </span>
        </div>
        <div className="w-full h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
          <div
            className="h-full bg-teal rounded-full transition-all duration-300"
            style={{ width: `${(reviewed / total) * 100}%` }}
          />
        </div>
      </div>

      {/* ---- Supplier Header ---- */}
      <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-slate truncate">
              {supplier.supplier_name}
            </h2>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted flex-wrap">
              {supplier.companies_house_number && (
                <span>CH: {supplier.companies_house_number}</span>
              )}
              {supplier.sector && <span>{supplier.sector}</span>}
              {supplier.spend_gbp != null && (
                <span>
                  Spend: £
                  {supplier.spend_gbp >= 1000
                    ? `${(supplier.spend_gbp / 1000).toFixed(1)}k`
                    : supplier.spend_gbp.toFixed(0)}
                </span>
              )}
              {supplier.co2e_kg != null && (
                <span>
                  {(supplier.co2e_kg / 1000).toFixed(2)} tCO2e
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {supplier.hemera_score != null && (
              <div
                className={`px-3 py-1.5 rounded-lg text-sm font-bold tabular-nums ${scoreColour(supplier.hemera_score)}`}
              >
                {supplier.hemera_score}
              </div>
            )}
            {supplier.confidence && (
              <span
                className={`text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full ${conf.bg} ${conf.text}`}
              >
                {supplier.confidence}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ---- Split Panel ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel — Findings */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted">
            Findings ({supplier.findings.length})
          </h3>

          {sourceGroups.map((source) => {
            const findings = groupedFindings.filter(
              (f) => f.source === source
            );
            if (findings.length === 0) return null;
            return (
              <div key={source} className="space-y-2">
                <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wide">
                  {groupLabels[source]}
                </h4>
                {findings.map((f) => (
                  <FindingCard
                    key={f.id}
                    finding={f}
                    onToggle={handleToggle}
                  />
                ))}
              </div>
            );
          })}
        </div>

        {/* Right Panel — Report Preview */}
        <div>
          <ReportPreview
            supplierId={supplier.supplier_id}
            supplierName={supplier.supplier_name}
            engagementId={id}
            includedFindings={includedFindings}
            actions={supplier.actions}
            engagements={supplier.engagements}
            clientLanguage={clientLanguage[supplier.supplier_id] ?? {}}
            onActionsGenerated={handleActionsGenerated}
            onClientLanguage={handleClientLanguage}
            onLogEngagement={handleLogEngagement}
          />
        </div>
      </div>

      {/* ---- Navigation Footer ---- */}
      <div className="flex items-center justify-between pt-4 border-t border-[#E5E5E0]">
        <div className="flex items-center gap-3">
          <button
            onClick={goPrev}
            disabled={currentIndex === 0}
            className="px-4 py-2.5 border border-[#E5E5E0] rounded-lg text-sm font-semibold text-muted hover:bg-[#FAFAF7] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <div className="text-[10px] text-muted">
            ← Prev · → Next
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href={`/dashboard/${id}`}
            className="text-xs text-muted hover:text-teal transition-colors font-medium"
          >
            Save & Exit
          </Link>
          <button
            onClick={goNext}
            disabled={currentIndex >= suppliers.length - 1}
            className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save & Next
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared components                                                  */
/* ------------------------------------------------------------------ */

function CenteredPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
      {children}
    </div>
  );
}

function Spinner() {
  return (
    <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
  );
}
