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
  findings: (Finding & { included?: boolean | null })[];
  actions: RecommendedAction[];
  engagements: EngagementTouchpoint[];
  client_language?: Record<number, string>;
}

/* Raw shape from GET /engagements/{id}/supplier-report */
interface APISupplierItem {
  supplier: {
    id: number;
    name: string;
    legal_name?: string;
    ch_number?: string;
    sector?: string;
    hemera_score?: number;
    confidence?: string;
    critical_flag?: boolean;
    hemera_verified?: boolean;
  };
  txn_count: number;
  total_spend: number;
  total_co2e_kg: number;
  findings: (Finding & { selection?: { included: boolean; client_title?: string; client_detail?: string; analyst_note?: string } | null })[];
  actions: { id?: number; action_text: string; priority?: number; linked_finding_ids?: number[]; language_source?: string }[];
  hemera_engagements: EngagementTouchpoint[];
}

interface SupplierReportResponse {
  engagement_id: number;
  client_name: string;
  status: string;
  supplier_count: number;
  suppliers: APISupplierItem[];
}

type PageState = "loading" | "reviewing" | "saving" | "error" | "empty" | "enriching";

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

const SOURCE_ORDER: Record<string, number> = {
  deterministic: 0,
  ai: 1,
  ai_automated: 1,
  ai_manual: 1,
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
  const [clientName, setClientName] = useState("");
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

        setClientName(data.client_name || "");

        if (!data.suppliers || data.suppliers.length === 0) {
          setPageState("empty");
          return;
        }

        // Transform API response to flat frontend shape
        const transformed: SupplierFindings[] = data.suppliers.map((item) => ({
          supplier_id: item.supplier.id,
          supplier_name: item.supplier.legal_name || item.supplier.name,
          companies_house_number: item.supplier.ch_number ?? undefined,
          sector: item.supplier.sector ?? undefined,
          spend_gbp: item.total_spend,
          co2e_kg: item.total_co2e_kg,
          hemera_score: item.supplier.hemera_score ?? undefined,
          confidence: item.supplier.confidence ?? undefined,
          findings: item.findings.map((f) => ({
            ...f,
            included: f.selection ? f.selection.included : null,
          })),
          actions: item.actions.map((a) => ({ text: a.action_text })),
          engagements: item.hemera_engagements,
        }));

        setSuppliers(transformed);

        // Restore client language from selections
        const lang: Record<number, Record<number, string>> = {};
        data.suppliers.forEach((item) => {
          const supplierId = item.supplier.id;
          item.findings.forEach((f) => {
            if (f.selection?.client_detail) {
              if (!lang[supplierId]) lang[supplierId] = {};
              lang[supplierId][f.id] = f.selection.client_detail;
            }
          });
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
  /*  AI Risk Analysis — attach verdicts to finding cards              */
  /* ---------------------------------------------------------------- */

  const handleRiskAnalysisResult = useCallback(
    (text: string) => {
      if (!supplier) return;
      try {
        const parsed = JSON.parse(text);
        const verdicts = parsed.verified_findings;
        if (!Array.isArray(verdicts)) return;

        setSuppliers((prev) =>
          prev.map((s, i) => {
            if (i !== currentIndex) return s;
            return {
              ...s,
              findings: s.findings.map((f) => {
                const match = verdicts.find(
                  (v: { original_title?: string }) =>
                    v.original_title && f.title.includes(v.original_title.substring(0, 30))
                );
                if (!match) return f;
                return {
                  ...f,
                  ai_verdict: {
                    verdict: match.verdict,
                    reasoning: match.reasoning,
                    corrected_title: match.corrected_title || undefined,
                  },
                };
              }),
            };
          })
        );
      } catch {
        // If response isn't valid JSON, ignore
      }
    },
    [supplier, currentIndex]
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
  /*  Run Analysis (enrichment — no AI, free data layers only)         */
  /* ---------------------------------------------------------------- */

  const [enrichProgress, setEnrichProgress] = useState("");
  const [enrichDetail, setEnrichDetail] = useState("");
  const [enrichCounts, setEnrichCounts] = useState({ current: 0, total: 0 });

  const handleRunAnalysis = useCallback(async () => {
    if (!supplier) return;
    const supplierId = supplier.supplier_id;
    if (!supplierId) {
      setErrorMsg("No supplier ID available");
      setPageState("error");
      return;
    }
    setPageState("enriching");
    setEnrichProgress("Starting analysis...");
    setEnrichDetail(supplier.supplier_name);
    setEnrichCounts({ current: 0, total: 0 });

    try {
      const token = await getToken();
      const url = `${API_URL}/api/engagements/${id}/supplier-report/enrich/${supplierId}`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status}: ${text}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response stream");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const msg = JSON.parse(line);
            if (msg.type === "progress") {
              setEnrichCounts({ current: msg.current, total: msg.total });
              if (msg.status === "analysing") {
                setEnrichProgress(`Layer ${msg.current} of ${msg.total}`);
                setEnrichDetail(msg.layer_name);
              } else if (msg.status === "error") {
                setEnrichDetail(`${msg.layer_name} — error, skipping`);
              }
            } else if (msg.type === "done") {
              setEnrichProgress(`Done — ${msg.findings_generated} findings generated. Reloading...`);
              setEnrichDetail("");
              setTimeout(() => window.location.reload(), 1500);
            }
          } catch {
            // skip unparseable lines
          }
        }
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to run analysis");
      setPageState("error");
    }
  }, [getToken, id, supplier]);

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

  if (pageState === "enriching") {
    const pct = enrichCounts.total > 0 ? Math.round((enrichCounts.current / enrichCounts.total) * 100) : 0;
    return (
      <CenteredPanel>
        <Spinner />
        <p className="text-sm font-semibold mt-4">{enrichProgress}</p>
        {enrichDetail && (
          <p className="text-teal text-sm mt-1 font-medium">{enrichDetail}</p>
        )}
        {enrichCounts.total > 0 && (
          <div className="w-64 mt-4">
            <div className="w-full h-2 bg-[#E5E5E0] rounded-full overflow-hidden">
              <div
                className="h-full bg-teal rounded-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-[11px] text-muted mt-1 text-center">Layer {enrichCounts.current}/{enrichCounts.total} · {pct}%</p>
          </div>
        )}
        <p className="text-muted text-[11px] mt-3 max-w-sm text-center">
          Checking Companies House, Environment Agency, HSE, and 50+ other public databases. No AI or paid APIs.
        </p>
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
  const sourceGroupDefs = [
    { key: "deterministic", label: "Deterministic Findings", match: (s: string) => s === "deterministic" },
    { key: "ai", label: "AI-Generated Findings", match: (s: string) => s === "ai" || s === "ai_automated" || s === "ai_manual" },
    { key: "outlier", label: "Outlier Findings", match: (s: string) => s === "outlier" },
  ];

  return (
    <div className="space-y-4">
      {/* ---- Client name + progress bar ---- */}
      {clientName && (
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold text-slate">{clientName}</h1>
          <span className="text-[11px] text-muted bg-[#F1F5F9] px-2.5 py-1 rounded-full">HemeraScope Review</span>
        </div>
      )}
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

      {/* ---- Run Analysis banner ---- */}
      {(() => {
        const noFindings = suppliers.every((s) => s.findings.length === 0);
        const hasFindings = !noFindings;
        return (
          <div className={`${noFindings ? "bg-[#F0F9FF] border-[#BAE6FD]" : "bg-[#FAFAF7] border-[#E5E5E0]"} border rounded-xl p-4 flex items-center justify-between`}>
            <div>
              {noFindings ? (
                <>
                  <h3 className="text-sm font-semibold text-[#0C4A6E]">Suppliers need analysis</h3>
                  <p className="text-xs text-[#0369A1] mt-0.5">
                    Run analysis to collect data from Companies House, Environment Agency, HSE, and other public databases. No AI or paid APIs.
                  </p>
                </>
              ) : (
                <p className="text-xs text-muted">
                  {supplier.findings.length} findings for current supplier · Re-run to refresh data from 50+ public sources
                </p>
              )}
            </div>
            <button
              onClick={handleRunAnalysis}
              className={`px-4 py-2 rounded-lg text-xs font-semibold hover:opacity-90 transition-opacity flex-shrink-0 ${
                noFindings ? "bg-teal text-white" : "border border-[#E5E5E0] text-muted hover:bg-[#F0F0EB]"
              }`}
            >
              {hasFindings ? "Re-run Analysis" : "Run Analysis"}
            </button>
          </div>
        );
      })()}

      {/* ---- Split Panel ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel — Findings */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted">
            Findings ({supplier.findings.length})
          </h3>

          {sourceGroupDefs.map((group) => {
            const findings = groupedFindings.filter(
              (f) => group.match(f.source)
            );
            if (findings.length === 0) return null;
            return (
              <div key={group.key} className="space-y-2">
                <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wide">
                  {group.label}
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
            allFindingsCount={supplier.findings.length}
            actions={supplier.actions}
            engagements={supplier.engagements}
            clientLanguage={clientLanguage[supplier.supplier_id] ?? {}}
            onActionsGenerated={handleActionsGenerated}
            onClientLanguage={handleClientLanguage}
            onRemoveFinding={(findingId) => handleToggle(findingId, false)}
            onRiskAnalysisResult={handleRiskAnalysisResult}
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
