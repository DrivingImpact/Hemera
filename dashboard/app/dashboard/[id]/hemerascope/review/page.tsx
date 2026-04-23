"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AITaskButtons from "@/components/ai-task-buttons";
import type { Finding } from "@/components/finding-card";
import type {
  RecommendedAction,
  EngagementTouchpoint,
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
  selections: Record<number, boolean>;
  actions: RecommendedAction[];
  engagements: EngagementTouchpoint[];
  client_language?: Record<number, string>;
}

/* Raw shape from GET /engagements/{id}/supplier-report — same as curation page */
interface APIFinding {
  id: number;
  source: string;
  domain: string;
  severity: Finding["severity"];
  title: string;
  detail: string;
  evidence_url?: string | null;
  layer?: number | null;
  source_name?: string | null;
  selection?: {
    included: boolean;
    client_title?: string | null;
    client_detail?: string | null;
    analyst_note?: string | null;
  } | null;
}

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
  };
  txn_count: number;
  total_spend: number;
  total_co2e_kg: number;
  findings: APIFinding[];
  actions: { id?: number; action_text: string; priority?: number; linked_finding_ids?: number[]; language_source?: string }[];
  hemera_engagements: EngagementTouchpoint[];
}

interface SupplierReportResponse {
  engagement_id?: number;
  client_name?: string;
  status?: string;
  supplier_count?: number;
  suppliers: APISupplierItem[];
  executive_summary?: string;
}

type PageState = "loading" | "ready" | "publishing" | "published" | "error";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreColour(score?: number): string {
  if (score == null) return "bg-[#F1F5F9] text-[#475569]";
  if (score >= 70) return "bg-[#D1FAE5] text-[#065F46]";
  if (score >= 40) return "bg-[#FEF3C7] text-[#92400E]";
  return "bg-[#FEE2E2] text-[#991B1B]";
}

function riskLevel(score?: number): { label: string; colour: string } {
  if (score == null) return { label: "Unknown", colour: "bg-[#F1F5F9] text-[#475569]" };
  if (score >= 70) return { label: "Strong", colour: "bg-[#D1FAE5] text-[#065F46]" };
  if (score >= 40) return { label: "Needs Attention", colour: "bg-[#FEF3C7] text-[#92400E]" };
  return { label: "Critical", colour: "bg-[#FEE2E2] text-[#991B1B]" };
}

function severityBorder(severity: Finding["severity"]): string {
  switch (severity) {
    case "critical":
      return "border-l-[#DC2626]";
    case "high":
      return "border-l-[#F59E0B]";
    case "medium":
      return "border-l-[#EAB308]";
    case "info":
      return "border-l-[#3B82F6]";
    case "positive":
      return "border-l-[#059669]";
  }
}

function severityBadge(severity: Finding["severity"]): string {
  switch (severity) {
    case "critical":
      return "bg-[#FEE2E2] text-[#991B1B]";
    case "high":
      return "bg-[#FEF3C7] text-[#92400E]";
    case "medium":
      return "bg-[#FEF9C3] text-[#854D0E]";
    case "info":
      return "bg-[#EFF6FF] text-[#1E40AF]";
    case "positive":
      return "bg-[#D1FAE5] text-[#065F46]";
  }
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [pageState, setPageState] = useState<PageState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [suppliers, setSuppliers] = useState<SupplierFindings[]>([]);
  const [execSummary, setExecSummary] = useState("");
  const [activeSection, setActiveSection] = useState("executive-summary");

  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

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
  /*  Load data                                                        */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiFetch<SupplierReportResponse>(
          `/engagements/${id}/supplier-report`
        );

        if (!data.suppliers || data.suppliers.length === 0) {
          setPageState("error");
          setErrorMsg("No supplier data found. Complete the curation stage first.");
          return;
        }

        // Transform APISupplierItem shape → flat SupplierFindings shape.
        // Specifically: build a selections map (finding_id → included) from
        // each finding's nested selection field, and promote supplier fields.
        const transformed: SupplierFindings[] = data.suppliers.map((item) => {
          const selections: Record<number, boolean> = {};
          const clientLang: Record<number, string> = {};
          for (const f of item.findings) {
            if (f.selection) {
              selections[f.id] = f.selection.included;
              if (f.selection.client_detail) {
                clientLang[f.id] = f.selection.client_detail;
              }
            }
          }
          return {
            supplier_id: item.supplier.id,
            supplier_name: item.supplier.legal_name || item.supplier.name,
            companies_house_number: item.supplier.ch_number ?? undefined,
            sector: item.supplier.sector ?? undefined,
            spend_gbp: item.total_spend,
            co2e_kg: item.total_co2e_kg,
            hemera_score: item.supplier.hemera_score ?? undefined,
            confidence: item.supplier.confidence ?? undefined,
            findings: item.findings.map((f) => ({
              id: f.id,
              source: f.source,
              domain: f.domain,
              severity: f.severity,
              title: f.title,
              detail: f.detail,
              evidence_url: f.evidence_url ?? undefined,
              layer: f.layer ?? undefined,
              source_name: f.source_name ?? undefined,
              included: f.selection ? f.selection.included : undefined,
            })) as Finding[],
            selections,
            actions: item.actions.map((a) => ({ text: a.action_text })),
            engagements: item.hemera_engagements ?? [],
            client_language: clientLang,
          };
        });

        setSuppliers(transformed);
        setExecSummary(data.executive_summary ?? "");
        setPageState("ready");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load");
        setPageState("error");
      }
    };
    load();
  }, [apiFetch, id]);

  /* ---------------------------------------------------------------- */
  /*  TOC data                                                         */
  /* ---------------------------------------------------------------- */

  const tocSections = useMemo(() => {
    const sections: { id: string; label: string }[] = [
      { id: "executive-summary", label: "Executive Summary" },
      { id: "methodology", label: "Methodology" },
    ];
    suppliers.forEach((s) => {
      sections.push({
        id: `supplier-${s.supplier_id}`,
        label: s.supplier_name,
      });
    });
    sections.push({ id: "recommendations", label: "Recommendations" });
    return sections;
  }, [suppliers]);

  /* ---------------------------------------------------------------- */
  /*  Scroll to section                                                */
  /* ---------------------------------------------------------------- */

  const scrollToSection = useCallback((sectionId: string) => {
    setActiveSection(sectionId);
    const el = sectionRefs.current[sectionId];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  /* ---------------------------------------------------------------- */
  /*  Publish                                                          */
  /* ---------------------------------------------------------------- */

  const handlePublish = useCallback(async () => {
    setPageState("publishing");
    try {
      await apiFetch(`/engagements/${id}/supplier-report/publish`, {
        method: "POST",
      });
      setPageState("published");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to publish");
      setPageState("error");
    }
  }, [apiFetch, id]);

  /* ---------------------------------------------------------------- */
  /*  Included findings per supplier                                   */
  /* ---------------------------------------------------------------- */

  const includedBySupplier = useMemo(() => {
    const map: Record<number, Finding[]> = {};
    suppliers.forEach((s) => {
      map[s.supplier_id] = s.findings.filter(
        (f) => s.selections[f.id] === true || f.included === true
      );
    });
    return map;
  }, [suppliers]);

  /* ---------------------------------------------------------------- */
  /*  Render states                                                    */
  /* ---------------------------------------------------------------- */

  if (pageState === "loading") {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
        <p className="text-muted text-sm mt-3">Loading report preview...</p>
      </div>
    );
  }

  if (pageState === "error") {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <p className="text-error text-sm">{errorMsg}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (pageState === "published") {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-16 h-16 rounded-full bg-[#D1FAE5] flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">Report Published</h2>
        <p className="text-muted text-sm mt-1">
          The report is now visible on the client dashboard.
        </p>
        <Link
          href={`/dashboard/${id}/hemerascope/report`}
          className="mt-5 px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          View Client Report
        </Link>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Main layout                                                      */
  /* ---------------------------------------------------------------- */

  return (
    <div className="flex gap-6 min-h-[calc(100vh-200px)]">
      {/* ---- Left Sidebar: Table of Contents ---- */}
      <aside className="w-56 flex-shrink-0 print:hidden">
        <div className="sticky top-4">
          <h3 className="text-[11px] font-bold uppercase tracking-wide text-muted mb-3">
            Table of Contents
          </h3>
          <nav className="space-y-0.5">
            {tocSections.map((s) => (
              <button
                key={s.id}
                onClick={() => scrollToSection(s.id)}
                className={`block w-full text-left px-3 py-2 rounded-lg text-xs transition-colors truncate ${
                  activeSection === s.id
                    ? "bg-teal/10 text-teal font-semibold"
                    : "text-muted hover:bg-[#FAFAF7] hover:text-slate"
                }`}
              >
                {s.label}
              </button>
            ))}
          </nav>

          {/* Back to curation link */}
          <div className="mt-6 pt-4 border-t border-[#E5E5E0]">
            <Link
              href={`/dashboard/${id}/hemerascope`}
              className="flex items-center gap-1.5 text-xs text-muted hover:text-teal transition-colors font-medium"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Curation
            </Link>
          </div>
        </div>
      </aside>

      {/* ---- Right Content: Report Preview ---- */}
      <div className="flex-1 min-w-0 space-y-8">
        {/* Executive Summary */}
        <section
          ref={(el) => { sectionRefs.current["executive-summary"] = el; }}
          className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6"
        >
          <h2 className="text-base font-bold text-slate mb-4">Executive Summary</h2>
          {execSummary ? (
            <div className="text-sm text-slate leading-relaxed whitespace-pre-wrap">
              {execSummary}
            </div>
          ) : (
            <div className="text-sm text-muted bg-[#FAFAF7] rounded-lg px-4 py-6 text-center">
              No executive summary generated yet.
            </div>
          )}
          <div className="mt-4">
            <AITaskButtons
              taskType="executive_summary"
              targetType="engagement"
              targetId={Number(id) || 0}
              context={{
                supplier_count: suppliers.length,
                suppliers: suppliers.map((s) => ({
                  name: s.supplier_name,
                  score: s.hemera_score,
                  findings_count: (includedBySupplier[s.supplier_id] ?? []).length,
                })),
              }}
              onResult={(text) => setExecSummary(text)}
            />
          </div>
        </section>

        {/* Methodology */}
        <section
          ref={(el) => { sectionRefs.current["methodology"] = el; }}
          className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6"
        >
          <h2 className="text-base font-bold text-slate mb-3">Methodology</h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              This report was produced using Hemera&apos;s proprietary supplier
              intelligence methodology, combining deterministic data checks, AI
              analysis, and outlier detection across seven assessment domains.
            </p>
            <p>
              Each supplier receives a Hemera Score (0-100) based on weighted
              findings across Environment, Social, Governance, Financial Health,
              Cyber Security, Modern Slavery, and Regulatory Compliance.
            </p>
            <p>
              Findings have been reviewed and curated by a Hemera analyst to
              ensure accuracy and relevance before inclusion in this report.
            </p>
          </div>
        </section>

        {/* Per-supplier sections */}
        {suppliers.map((supplier) => {
          const included = includedBySupplier[supplier.supplier_id] ?? [];
          const risk = riskLevel(supplier.hemera_score);
          const langMap = supplier.client_language ?? {};

          return (
            <section
              key={supplier.supplier_id}
              ref={(el) => { sectionRefs.current[`supplier-${supplier.supplier_id}`] = el; }}
              className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6 space-y-5"
            >
              {/* Supplier header */}
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2 className="text-base font-bold text-slate">
                    {supplier.supplier_name}
                  </h2>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted flex-wrap">
                    {supplier.sector && <span>{supplier.sector}</span>}
                    {supplier.spend_gbp != null && (
                      <span>
                        Spend: {"\u00A3"}
                        {supplier.spend_gbp >= 1000
                          ? `${(supplier.spend_gbp / 1000).toFixed(1)}k`
                          : supplier.spend_gbp.toFixed(0)}
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
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full ${risk.colour}`}
                  >
                    {risk.label}
                  </span>
                </div>
              </div>

              {/* Included findings */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wide text-muted mb-3">
                  Key Findings ({included.length})
                </h3>
                {included.length === 0 ? (
                  <p className="text-sm text-muted bg-[#FAFAF7] rounded-lg px-4 py-4 text-center">
                    No findings included for this supplier.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {included.map((f) => (
                      <div
                        key={f.id}
                        className={`border-l-4 ${severityBorder(f.severity)} bg-[#FAFAF7] rounded-lg p-3`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${severityBadge(f.severity)}`}
                          >
                            {f.severity}
                          </span>
                          <span className="text-[10px] text-muted">{f.domain}</span>
                        </div>
                        <p className="text-sm font-medium text-slate">{f.title}</p>
                        {langMap[f.id] ? (
                          <p className="text-xs text-muted mt-1 leading-relaxed">
                            {langMap[f.id]}
                          </p>
                        ) : (
                          <p className="text-xs text-muted mt-1 leading-relaxed">
                            {f.detail}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recommended actions */}
              {supplier.actions.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wide text-muted mb-3">
                    Recommended Actions
                  </h3>
                  <ol className="space-y-2">
                    {supplier.actions.map((action, i) => (
                      <li
                        key={action.id ?? i}
                        className="flex items-start gap-3 text-sm text-slate"
                      >
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-teal/10 text-teal text-[10px] font-bold flex items-center justify-center mt-0.5">
                          {i + 1}
                        </span>
                        <span className="leading-relaxed">{action.text}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Engagement status */}
              {supplier.engagements.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wide text-muted mb-3">
                    Engagement Status ({supplier.engagements.length} touchpoint
                    {supplier.engagements.length !== 1 ? "s" : ""})
                  </h3>
                  <div className="space-y-1.5">
                    {supplier.engagements.slice(0, 3).map((eng) => (
                      <div
                        key={eng.id}
                        className="flex items-center gap-2 text-xs text-muted"
                      >
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[#475569]">
                          {eng.engagement_type}
                        </span>
                        <span className="truncate">{eng.subject}</span>
                        {eng.created_at && (
                          <span className="flex-shrink-0 ml-auto">
                            {new Date(eng.created_at).toLocaleDateString("en-GB", {
                              day: "numeric", month: "short", year: "numeric",
                            })}
                          </span>
                        )}
                      </div>
                    ))}
                    {supplier.engagements.length > 3 && (
                      <p className="text-[11px] text-muted">
                        + {supplier.engagements.length - 3} more touchpoints
                      </p>
                    )}
                  </div>
                </div>
              )}
            </section>
          );
        })}

        {/* Recommendations */}
        <section
          ref={(el) => { sectionRefs.current["recommendations"] = el; }}
          className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6"
        >
          <h2 className="text-base font-bold text-slate mb-3">Recommendations</h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              Based on the analysis above, we recommend focusing engagement
              efforts on suppliers with Critical risk ratings. Hemera can
              facilitate direct supplier engagement through our managed service
              offering.
            </p>
          </div>
          <div className="mt-4">
            <AITaskButtons
              taskType="report_recommendations"
              targetType="engagement"
              targetId={Number(id) || 0}
              context={{
                suppliers: suppliers.map((s) => ({
                  name: s.supplier_name,
                  score: s.hemera_score,
                  actions_count: s.actions.length,
                  findings_count: (includedBySupplier[s.supplier_id] ?? []).length,
                })),
              }}
              onResult={() => {}}
            />
          </div>
        </section>

        {/* ---- Bottom Actions ---- */}
        <div className="flex items-center justify-between pt-4 pb-8 border-t border-[#E5E5E0]">
          <a
            href={`${API_URL}/api/engagements/${id}/supplier-intelligence/pdf`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 border border-[#E5E5E0] rounded-lg text-sm font-semibold text-slate hover:bg-[#FAFAF7] transition-colors inline-flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export PDF
          </a>
          <button
            onClick={handlePublish}
            disabled={pageState === "publishing"}
            className="px-6 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 inline-flex items-center gap-2"
          >
            {pageState === "publishing" ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Publishing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Publish to Client Dashboard
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
