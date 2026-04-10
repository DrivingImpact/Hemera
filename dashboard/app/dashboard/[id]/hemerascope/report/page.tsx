"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SupplierSummary {
  supplier_id: number;
  supplier_name: string;
  sector?: string;
  spend_gbp?: number;
  hemera_score?: number;
  risk_level?: string;
  findings_summary?: string;
  engagement_count?: number;
  hemera_verified?: boolean;
}

interface SupplierIntelligenceResponse {
  suppliers: SupplierSummary[];
}

type SortField = "score" | "spend" | "name";
type SortDir = "asc" | "desc";
type RiskFilter = "all" | "critical" | "needs_attention" | "strong";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreColour(score?: number): string {
  if (score == null) return "bg-[#F1F5F9] text-[#475569]";
  if (score >= 70) return "bg-[#D1FAE5] text-[#065F46]";
  if (score >= 40) return "bg-[#FEF3C7] text-[#92400E]";
  return "bg-[#FEE2E2] text-[#991B1B]";
}

function riskBadge(score?: number): { label: string; colour: string } {
  if (score == null) return { label: "Unknown", colour: "bg-[#F1F5F9] text-[#475569]" };
  if (score >= 70) return { label: "Strong", colour: "bg-[#D1FAE5] text-[#065F46]" };
  if (score >= 40) return { label: "Needs Attention", colour: "bg-[#FEF3C7] text-[#92400E]" };
  return { label: "Critical", colour: "bg-[#FEE2E2] text-[#991B1B]" };
}

function riskFromScore(score?: number): RiskFilter {
  if (score == null) return "strong";
  if (score >= 70) return "strong";
  if (score >= 40) return "needs_attention";
  return "critical";
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function ClientReportPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [suppliers, setSuppliers] = useState<SupplierSummary[]>([]);
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  /* ---------------------------------------------------------------- */
  /*  Load data                                                        */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    const load = async () => {
      try {
        const token = await getToken();
        const res = await fetch(
          `${API_URL}/api/engagements/${id}/supplier-intelligence`,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `API error ${res.status}`);
        }
        const data: SupplierIntelligenceResponse = await res.json();
        setSuppliers(data.suppliers ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [getToken, id]);

  /* ---------------------------------------------------------------- */
  /*  Filter and sort                                                  */
  /* ---------------------------------------------------------------- */

  const filtered = useMemo(() => {
    let list = [...suppliers];
    if (riskFilter !== "all") {
      list = list.filter((s) => riskFromScore(s.hemera_score) === riskFilter);
    }
    list.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "score":
          cmp = (a.hemera_score ?? 0) - (b.hemera_score ?? 0);
          break;
        case "spend":
          cmp = (a.spend_gbp ?? 0) - (b.spend_gbp ?? 0);
          break;
        case "name":
          cmp = (a.supplier_name ?? "").localeCompare(b.supplier_name ?? "");
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [suppliers, riskFilter, sortField, sortDir]);

  /* ---------------------------------------------------------------- */
  /*  Toggle sort                                                      */
  /* ---------------------------------------------------------------- */

  const toggleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortField(field);
        setSortDir(field === "name" ? "asc" : "desc");
      }
    },
    [sortField]
  );

  const sortIcon = (field: SortField) => {
    if (sortField !== field) return null;
    return sortDir === "asc" ? " \u2191" : " \u2193";
  };

  /* ---------------------------------------------------------------- */
  /*  Render states                                                    */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
        <p className="text-muted text-sm mt-3">Loading supplier overview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <p className="text-error text-sm">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (suppliers.length === 0) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-16 h-16 rounded-full bg-[#F1F5F9] flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-[#64748B]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">No Published Report</h2>
        <p className="text-muted text-sm mt-1">
          The supplier intelligence report has not been published yet.
        </p>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Risk counts                                                      */
  /* ---------------------------------------------------------------- */

  const riskCounts = suppliers.reduce(
    (acc, s) => {
      const r = riskFromScore(s.hemera_score);
      acc[r] = (acc[r] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  /* ---------------------------------------------------------------- */
  /*  Main                                                             */
  /* ---------------------------------------------------------------- */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate">Supplier Intelligence Report</h1>
          <p className="text-sm text-muted mt-0.5">
            {suppliers.length} supplier{suppliers.length !== 1 ? "s" : ""} assessed
          </p>
        </div>
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
      </div>

      {/* Risk summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <button
          onClick={() => setRiskFilter(riskFilter === "critical" ? "all" : "critical")}
          className={`rounded-xl border p-4 text-left transition-all ${
            riskFilter === "critical"
              ? "border-[#DC2626] bg-[#FEF2F2]"
              : "border-[#E5E5E0] bg-surface hover:border-[#DC2626]/30"
          }`}
        >
          <p className="text-2xl font-bold text-[#991B1B]">{riskCounts.critical ?? 0}</p>
          <p className="text-xs font-semibold text-[#991B1B] mt-0.5">Critical</p>
        </button>
        <button
          onClick={() => setRiskFilter(riskFilter === "needs_attention" ? "all" : "needs_attention")}
          className={`rounded-xl border p-4 text-left transition-all ${
            riskFilter === "needs_attention"
              ? "border-[#F59E0B] bg-[#FFFBEB]"
              : "border-[#E5E5E0] bg-surface hover:border-[#F59E0B]/30"
          }`}
        >
          <p className="text-2xl font-bold text-[#92400E]">{riskCounts.needs_attention ?? 0}</p>
          <p className="text-xs font-semibold text-[#92400E] mt-0.5">Needs Attention</p>
        </button>
        <button
          onClick={() => setRiskFilter(riskFilter === "strong" ? "all" : "strong")}
          className={`rounded-xl border p-4 text-left transition-all ${
            riskFilter === "strong"
              ? "border-[#059669] bg-[#ECFDF5]"
              : "border-[#E5E5E0] bg-surface hover:border-[#059669]/30"
          }`}
        >
          <p className="text-2xl font-bold text-[#065F46]">{riskCounts.strong ?? 0}</p>
          <p className="text-xs font-semibold text-[#065F46] mt-0.5">Strong</p>
        </button>
      </div>

      {/* Table */}
      <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E5E0] bg-[#FAFAF7]">
                <th
                  onClick={() => toggleSort("name")}
                  className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted cursor-pointer hover:text-slate select-none"
                >
                  Supplier{sortIcon("name")}
                </th>
                <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted">
                  Sector
                </th>
                <th
                  onClick={() => toggleSort("spend")}
                  className="text-right px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted cursor-pointer hover:text-slate select-none"
                >
                  Spend{sortIcon("spend")}
                </th>
                <th
                  onClick={() => toggleSort("score")}
                  className="text-center px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted cursor-pointer hover:text-slate select-none"
                >
                  Hemera Score{sortIcon("score")}
                </th>
                <th className="text-center px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted">
                  Risk Level
                </th>
                <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted">
                  Key Findings
                </th>
                <th className="text-center px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted">
                  Engagements
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0F0EB]">
              {filtered.map((s) => {
                const risk = riskBadge(s.hemera_score);
                return (
                  <tr
                    key={s.supplier_id}
                    className="hover:bg-[#FAFAF7] transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-slate">
                      {s.supplier_name}
                    </td>
                    <td className="px-4 py-3 text-muted text-xs">
                      {s.sector ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-right text-muted tabular-nums">
                      {s.spend_gbp != null
                        ? `\u00A3${s.spend_gbp >= 1000 ? `${(s.spend_gbp / 1000).toFixed(1)}k` : s.spend_gbp.toFixed(0)}`
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold tabular-nums ${scoreColour(s.hemera_score)}`}
                      >
                        {s.hemera_score ?? "-"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full ${risk.colour}`}
                      >
                        {risk.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted max-w-[200px]">
                      {s.findings_summary
                        ? truncate(s.findings_summary, 80)
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-muted tabular-nums">
                      {s.engagement_count ?? 0}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/dashboard/${id}/hemerascope/report/${s.supplier_id}`}
                        className="text-xs text-teal font-semibold hover:underline whitespace-nowrap"
                      >
                        View detail {"\u2192"}
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-8 text-center text-sm text-muted"
                  >
                    No suppliers match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
