"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DomainScore {
  domain: string;
  score: number;
  max_score: number;
}

interface FindingDetail {
  id: number;
  title: string;
  detail: string;
  severity: "critical" | "high" | "medium" | "info" | "positive";
  domain: string;
  client_language?: string;
}

interface RecommendedAction {
  id?: number;
  text: string;
  priority?: "high" | "medium" | "low";
}

interface EngagementTouchpoint {
  id: number;
  date: string;
  type: string;
  notes: string;
}

interface SupplierDetail {
  supplier_id: number;
  supplier_name: string;
  sector?: string;
  spend_gbp?: number;
  hemera_score?: number;
  hemera_verified?: boolean;
  domain_scores?: DomainScore[];
  findings?: FindingDetail[];
  actions?: RecommendedAction[];
  engagements?: EngagementTouchpoint[];
  engagement_narrative?: string;
}

interface SupplierIntelligenceResponse {
  suppliers: SupplierDetail[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreColour(score?: number): string {
  if (score == null) return "bg-[#F1F5F9] text-[#475569]";
  if (score >= 70) return "bg-[#D1FAE5] text-[#065F46]";
  if (score >= 40) return "bg-[#FEF3C7] text-[#92400E]";
  return "bg-[#FEE2E2] text-[#991B1B]";
}

function domainColour(score: number, max: number): string {
  const pct = max > 0 ? (score / max) * 100 : 0;
  if (pct >= 70) return "bg-[#D1FAE5] border-[#059669] text-[#065F46]";
  if (pct >= 40) return "bg-[#FEF3C7] border-[#F59E0B] text-[#92400E]";
  return "bg-[#FEE2E2] border-[#DC2626] text-[#991B1B]";
}

function severityOrder(s: FindingDetail["severity"]): number {
  const order: Record<string, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    info: 3,
    positive: 4,
  };
  return order[s] ?? 5;
}

function severityBorder(severity: FindingDetail["severity"]): string {
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

function severityBadge(severity: FindingDetail["severity"]): string {
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

const DOMAIN_LABELS: Record<string, string> = {
  environment: "Environment",
  social: "Social",
  governance: "Governance",
  financial_health: "Financial Health",
  cyber_security: "Cyber Security",
  modern_slavery: "Modern Slavery",
  regulatory: "Regulatory",
};

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function SupplierDetailPage() {
  const { id, supplierId } = useParams<{ id: string; supplierId: string }>();
  const { getToken } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [supplier, setSupplier] = useState<SupplierDetail | null>(null);

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
        const found = data.suppliers?.find(
          (s) => String(s.supplier_id) === supplierId
        );
        if (!found) {
          throw new Error("Supplier not found in this report.");
        }
        setSupplier(found);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [getToken, id, supplierId]);

  /* ---------------------------------------------------------------- */
  /*  Render states                                                    */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
        <p className="text-muted text-sm mt-3">Loading supplier detail...</p>
      </div>
    );
  }

  if (error || !supplier) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <p className="text-error text-sm">{error || "Supplier not found."}</p>
        <Link
          href={`/dashboard/${id}/hemerascope/report`}
          className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90"
        >
          Back to Overview
        </Link>
      </div>
    );
  }

  const sortedFindings = [...(supplier.findings ?? [])].sort(
    (a, b) => severityOrder(a.severity) - severityOrder(b.severity)
  );

  const domains = supplier.domain_scores ?? [];

  /* ---------------------------------------------------------------- */
  /*  Main                                                             */
  /* ---------------------------------------------------------------- */

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back link */}
      <Link
        href={`/dashboard/${id}/hemerascope/report`}
        className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-teal transition-colors font-medium"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Supplier Overview
      </Link>

      {/* Header */}
      <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate">
                {supplier.supplier_name}
              </h1>
              {supplier.hemera_verified && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full bg-teal/10 text-teal">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Hemera Verified
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-xs text-muted flex-wrap">
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
          {supplier.hemera_score != null && (
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={`w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-bold tabular-nums ${scoreColour(supplier.hemera_score)}`}
              >
                {supplier.hemera_score}
              </div>
              <span className="text-[10px] text-muted mt-1 font-medium">
                Hemera Score
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Domain Score Breakdown */}
      {domains.length > 0 && (
        <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate mb-4">Domain Score Breakdown</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {domains.map((d) => (
              <div
                key={d.domain}
                className={`rounded-xl border-2 p-4 text-center ${domainColour(d.score, d.max_score)}`}
              >
                <p className="text-lg font-bold tabular-nums">
                  {d.score}
                  <span className="text-xs font-medium opacity-70">/{d.max_score}</span>
                </p>
                <p className="text-[11px] font-semibold mt-1">
                  {DOMAIN_LABELS[d.domain] ?? d.domain}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Findings */}
      <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6">
        <h2 className="text-sm font-bold text-slate mb-4">
          Key Findings ({sortedFindings.length})
        </h2>
        {sortedFindings.length === 0 ? (
          <p className="text-sm text-muted bg-[#FAFAF7] rounded-lg px-4 py-6 text-center">
            No findings available for this supplier.
          </p>
        ) : (
          <div className="space-y-3">
            {sortedFindings.map((f) => (
              <div
                key={f.id}
                className={`border-l-4 ${severityBorder(f.severity)} bg-[#FAFAF7] rounded-lg p-4`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span
                    className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${severityBadge(f.severity)}`}
                  >
                    {f.severity}
                  </span>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#F1F5F9] text-[#475569]">
                    {f.domain}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-slate">{f.title}</h3>
                <p className="text-xs text-muted mt-1 leading-relaxed">
                  {f.client_language ?? f.detail}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recommended Actions */}
      {(supplier.actions?.length ?? 0) > 0 && (
        <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate mb-4">Recommended Actions</h2>
          <ol className="space-y-3">
            {supplier.actions!.map((action, i) => (
              <li
                key={action.id ?? i}
                className="flex items-start gap-3"
              >
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal/10 text-teal text-xs font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  {action.priority && (
                    <span
                      className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded mr-2 ${
                        action.priority === "high"
                          ? "bg-[#FEE2E2] text-[#991B1B]"
                          : action.priority === "medium"
                            ? "bg-[#FEF3C7] text-[#92400E]"
                            : "bg-[#F1F5F9] text-[#475569]"
                      }`}
                    >
                      {action.priority}
                    </span>
                  )}
                  <span className="text-sm text-slate leading-relaxed">
                    {action.text}
                  </span>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-4 pt-4 border-t border-[#F0F0EB]">
            <p className="text-xs text-muted">
              Hemera can facilitate these actions through our managed supplier engagement
              service. Contact your account manager for details.
            </p>
          </div>
        </div>
      )}

      {/* Engagement Status */}
      {((supplier.engagements?.length ?? 0) > 0 || supplier.engagement_narrative) && (
        <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate mb-4">
            Hemera Engagement Status
          </h2>
          {supplier.engagement_narrative && (
            <p className="text-sm text-slate leading-relaxed mb-4">
              {supplier.engagement_narrative}
            </p>
          )}
          {(supplier.engagements?.length ?? 0) > 0 && (
            <div className="space-y-2">
              {supplier.engagements!.map((eng) => (
                <div
                  key={eng.id}
                  className="flex items-start gap-3 text-xs bg-[#FAFAF7] rounded-lg p-3"
                >
                  <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded bg-[#F1F5F9] text-[#475569] flex-shrink-0 mt-0.5">
                    {eng.type}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-slate leading-relaxed">{eng.notes}</p>
                    <p className="text-muted mt-1">{eng.date}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
