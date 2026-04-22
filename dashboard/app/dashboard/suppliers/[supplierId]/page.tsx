"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { SupplierDetail } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const LAYER_NAMES: Record<number, string> = {
  1: "Corporate Identity",
  2: "Ownership & Sanctions",
  3: "Financial Health",
  4: "Carbon & Environmental",
  5: "Labour & Ethics",
  6: "Certifications",
  7: "Adverse Media",
  9: "Government Contracts",
  10: "Water & Biodiversity",
  11: "Anti-Bribery",
  12: "Cyber Risk",
  13: "Social Value",
};

const ALL_LAYERS = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13];

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-tint text-[#991B1B]",
  high: "bg-[#FFF7ED] text-[#C2410C]",
  medium: "bg-amber-tint text-[#92400E]",
  info: "bg-[#DBEAFE] text-[#1E40AF]",
  positive: "bg-[#D1FAE5] text-[#065F46]",
};

/* ------------------------------------------------------------------ */
/*  Types for extended API response (beyond SupplierDetail)            */
/* ------------------------------------------------------------------ */

interface Finding {
  id: number;
  severity: string;
  domain: string;
  title: string;
  detail: string;
}

interface EngagementLink {
  id: number;
  org_name: string;
  status: string;
  created_at: string;
  spend_gbp: number;
  co2e_tonnes: number;
}

interface FullSupplierDetail extends SupplierDetail {
  findings?: Finding[];
  engagements?: EngagementLink[];
}

/* ------------------------------------------------------------------ */
/*  Score colour helper                                                */
/* ------------------------------------------------------------------ */

function scoreColour(score: number): string {
  if (score >= 80) return "text-[#065F46]";
  if (score >= 60) return "text-teal";
  if (score >= 40) return "text-[#92400E]";
  return "text-[#991B1B]";
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-[#D1FAE5]";
  if (score >= 60) return "bg-teal-tint";
  if (score >= 40) return "bg-amber-tint";
  return "bg-red-tint";
}

/* ------------------------------------------------------------------ */
/*  Collapsible section                                                */
/* ------------------------------------------------------------------ */

function Collapsible({
  title,
  badge,
  defaultOpen = false,
  children,
  muted = false,
}: {
  title: React.ReactNode;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  muted?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`border border-[#E5E5E0] rounded-xl overflow-hidden ${muted ? "opacity-50" : ""}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[#FAFAF8] transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`text-muted transition-transform ${open ? "rotate-90" : ""}`}
          >
            <polyline points="9,18 15,12 9,6" />
          </svg>
          <span className={`text-sm font-semibold ${muted ? "text-muted" : ""}`}>{title}</span>
        </div>
        {badge}
      </button>
      {open && <div className="px-4 pb-4 border-t border-[#E5E5E0]">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page component                                                */
/* ------------------------------------------------------------------ */

export default function SupplierDetailPage() {
  const { supplierId } = useParams<{ supplierId: string }>();
  const { getToken } = useAuth();

  const [supplier, setSupplier] = useState<FullSupplierDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [enrichMsg, setEnrichMsg] = useState<string | null>(null);

  // Filters for findings
  const [domainFilter, setDomainFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

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
        const body = await res.text();
        throw new Error(`API error ${res.status}: ${body}`);
      }
      return res.json();
    },
    [getToken],
  );

  // Fetch supplier data
  useEffect(() => {
    if (!supplierId) return;
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        const data = await apiFetch<FullSupplierDetail>(`/suppliers/${supplierId}`);
        if (!cancelled) setSupplier(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load supplier");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [supplierId, apiFetch]);

  // Rerun analysis
  const handleRerun = async () => {
    if (!supplierId) return;
    setEnriching(true);
    setEnrichMsg(null);
    try {
      await apiFetch(`/suppliers/${supplierId}/enrich`, { method: "POST" });
      setEnrichMsg("Enrichment started. Refresh in a few minutes to see updated results.");
      // Re-fetch after a short delay
      setTimeout(async () => {
        try {
          const data = await apiFetch<FullSupplierDetail>(`/suppliers/${supplierId}`);
          setSupplier(data);
        } catch {
          // silent — user can refresh manually
        }
        setEnriching(false);
      }, 3000);
    } catch (err) {
      setEnrichMsg(err instanceof Error ? err.message : "Failed to start enrichment");
      setEnriching(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Loading / error states                                           */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <div className="w-6 h-6 mx-auto rounded-full border-2 border-teal/30 border-t-teal animate-spin" />
          <p className="text-muted text-sm mt-3">Loading supplier...</p>
        </div>
      </div>
    );
  }

  if (error || !supplier) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-[#991B1B] text-sm">{error || "Supplier not found"}</p>
          <Link
            href="/dashboard/suppliers"
            className="text-teal text-xs font-semibold hover:underline mt-2 inline-block"
          >
            Back to suppliers
          </Link>
        </div>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Derived data                                                     */
  /* ---------------------------------------------------------------- */

  const sourcesByLayer = new Map<number, typeof supplier.sources>();
  for (const s of supplier.sources ?? []) {
    const existing = sourcesByLayer.get(s.layer) ?? [];
    existing.push(s);
    sourcesByLayer.set(s.layer, existing);
  }

  const findings = supplier.findings ?? [];
  const domains = [...new Set(findings.map((f) => f.domain))].sort();
  const severities = [...new Set(findings.map((f) => f.severity))].sort();

  const filteredFindings = findings.filter((f) => {
    if (domainFilter !== "all" && f.domain !== domainFilter) return false;
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    return true;
  });

  const latestScore = supplier.score_history?.[supplier.score_history.length - 1];

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href="/dashboard/suppliers"
        className="text-[12px] text-teal font-semibold hover:underline inline-block"
      >
        &larr; Back to suppliers
      </Link>

      {/* ============================================================ */}
      {/*  HEADER                                                       */}
      {/* ============================================================ */}
      <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-bold truncate">{supplier.name}</h1>
            {supplier.legal_name && supplier.legal_name !== supplier.name && (
              <p className="text-muted text-sm mt-0.5">{supplier.legal_name}</p>
            )}
            {supplier.ch_number && (
              <p className="text-xs text-muted mt-1">CH: {supplier.ch_number}</p>
            )}
            <div className="flex gap-2 mt-3 flex-wrap">
              <Badge variant={supplier.status === "enriched" ? "green" : "slate"}>
                {supplier.status}
              </Badge>
              {supplier.entity_type && <Badge variant="slate">{supplier.entity_type}</Badge>}
              {supplier.sector && <Badge variant="teal">{supplier.sector}</Badge>}
              {supplier.critical_flag && <Badge variant="red">Critical</Badge>}
            </div>
            {supplier.registered_address && (
              <p className="text-sm text-muted mt-3">{supplier.registered_address}</p>
            )}
            {supplier.sic_codes && supplier.sic_codes.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {supplier.sic_codes.map((code) => (
                  <span
                    key={code}
                    className="text-[10px] bg-paper text-muted px-1.5 py-0.5 rounded font-medium"
                  >
                    SIC {code}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Score + rerun */}
          <div className="flex-shrink-0 text-right space-y-3">
            <div>
              <div className="text-[10px] uppercase tracking-[1px] text-muted">Hemera Score</div>
              <div className={`text-4xl font-extrabold ${scoreColour(supplier.hemera_score)}`}>
                {supplier.hemera_score?.toFixed(0) ?? "—"}
              </div>
              {supplier.confidence && (
                <Badge
                  variant={
                    supplier.confidence === "high"
                      ? "green"
                      : supplier.confidence === "medium"
                        ? "amber"
                        : "slate"
                  }
                >
                  {supplier.confidence} confidence
                </Badge>
              )}
            </div>
            <button
              onClick={handleRerun}
              disabled={enriching}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-teal text-white hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {enriching ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  Running...
                </span>
              ) : (
                "Rerun analysis"
              )}
            </button>
            {enrichMsg && (
              <p className="text-[11px] text-muted mt-1 max-w-[200px]">{enrichMsg}</p>
            )}
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/*  ENRICHMENT LAYERS                                            */}
      {/* ============================================================ */}
      <div className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">
          Enrichment Layers
        </h2>
        <div className="space-y-2">
          {ALL_LAYERS.map((layerNum) => {
            const sources = sourcesByLayer.get(layerNum);
            const hasData = sources && sources.length > 0;
            const layerName = LAYER_NAMES[layerNum] || `Layer ${layerNum}`;

            return (
              <Collapsible
                key={layerNum}
                muted={!hasData}
                title={`Layer ${layerNum}: ${layerName}`}
                badge={
                  hasData ? (
                    <Badge variant="green">
                      {sources.length} source{sources.length !== 1 ? "s" : ""}
                    </Badge>
                  ) : (
                    <span className="text-[10px] text-muted italic">Not analysed</span>
                  )
                }
              >
                {hasData ? (
                  <div className="space-y-3 pt-3">
                    {sources.map((src, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold">{src.source_name}</span>
                          <span className="text-[10px] bg-paper text-muted px-1.5 py-0.5 rounded">
                            Tier {src.tier}
                          </span>
                          {src.is_verified && <Badge variant="green">Verified</Badge>}
                        </div>
                        <p className="text-sm text-muted">{src.summary}</p>
                        <p className="text-[10px] text-muted">
                          Fetched {new Date(src.fetched_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted pt-3">
                    No data collected for this layer yet.
                  </p>
                )}
              </Collapsible>
            );
          })}
        </div>
      </div>

      {/* ============================================================ */}
      {/*  FINDINGS                                                     */}
      {/* ============================================================ */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">Findings</h2>

        {findings.length > 0 ? (
          <>
            {/* Filters */}
            <div className="flex items-center gap-3 flex-wrap">
              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="text-xs border border-[#E5E5E0] rounded-lg px-3 py-1.5 bg-surface text-muted outline-none"
              >
                <option value="all">All domains</option>
                {domains.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="text-xs border border-[#E5E5E0] rounded-lg px-3 py-1.5 bg-surface text-muted outline-none"
              >
                <option value="all">All severities</option>
                {severities.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              {(domainFilter !== "all" || severityFilter !== "all") && (
                <button
                  onClick={() => {
                    setDomainFilter("all");
                    setSeverityFilter("all");
                  }}
                  className="text-[11px] text-teal font-semibold hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>

            {/* Finding cards */}
            <div className="space-y-2">
              {filteredFindings.map((f) => (
                <div
                  key={f.id}
                  className="bg-surface rounded-xl border border-[#E5E5E0] p-4 space-y-1"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.info}`}
                    >
                      {f.severity}
                    </span>
                    <span className="text-[10px] bg-paper text-muted px-1.5 py-0.5 rounded font-medium">
                      {f.domain}
                    </span>
                  </div>
                  <p className="text-sm font-semibold">{f.title}</p>
                  <p className="text-sm text-muted">{f.detail}</p>
                </div>
              ))}
              {filteredFindings.length === 0 && (
                <p className="text-sm text-muted italic">No findings match the selected filters.</p>
              )}
            </div>
          </>
        ) : (
          <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6 text-center">
            <p className="text-sm text-muted">No findings recorded for this supplier.</p>
          </div>
        )}
      </div>

      {/* ============================================================ */}
      {/*  SCORE HISTORY                                                */}
      {/* ============================================================ */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">
          Score History
        </h2>

        {supplier.score_history && supplier.score_history.length > 0 ? (
          <div className="space-y-2">
            {[...supplier.score_history].reverse().map((entry, idx) => (
              <div
                key={idx}
                className="bg-surface rounded-xl border border-[#E5E5E0] p-4 flex items-start gap-4"
              >
                {/* Score pill */}
                <div
                  className={`flex-shrink-0 w-14 h-14 rounded-xl flex items-center justify-center text-lg font-extrabold ${scoreBg(entry.hemera_score)} ${scoreColour(entry.hemera_score)}`}
                >
                  {entry.hemera_score.toFixed(0)}
                </div>
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold">
                      {new Date(entry.scored_at).toLocaleDateString("en-GB", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <Badge
                      variant={
                        entry.confidence === "high"
                          ? "green"
                          : entry.confidence === "medium"
                            ? "amber"
                            : "slate"
                      }
                    >
                      {entry.confidence}
                    </Badge>
                    {entry.critical_flag && <Badge variant="red">Critical</Badge>}
                    <span className="text-[10px] text-muted">
                      {entry.layers_completed} layer{entry.layers_completed !== 1 ? "s" : ""} completed
                    </span>
                  </div>
                  {/* Domain scores */}
                  {entry.domains && Object.keys(entry.domains).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {Object.entries(entry.domains).map(([domain, score]) => (
                        <span
                          key={domain}
                          className="text-[10px] bg-paper text-muted px-1.5 py-0.5 rounded"
                        >
                          {domain}: <span className="font-semibold">{score}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6 text-center">
            <p className="text-sm text-muted">No score history available.</p>
          </div>
        )}
      </div>

      {/* ============================================================ */}
      {/*  ENGAGEMENTS                                                  */}
      {/* ============================================================ */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">
          Engagements
        </h2>

        {supplier.engagements && supplier.engagements.length > 0 ? (
          <div className="space-y-2">
            {supplier.engagements.map((eng) => (
              <Link
                key={eng.id}
                href={`/dashboard/${eng.id}`}
                className="block bg-surface rounded-xl border border-[#E5E5E0] p-4 hover:border-teal/30 transition-all"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold truncate">{eng.org_name}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted">
                      <Badge
                        variant={eng.status === "released" ? "green" : eng.status === "processing" ? "amber" : "slate"}
                      >
                        {eng.status}
                      </Badge>
                      <span>
                        {new Date(eng.created_at).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="flex-shrink-0 text-right space-y-0.5">
                    {eng.spend_gbp != null && eng.spend_gbp > 0 && (
                      <p className="text-xs text-muted">
                        Spend:{" "}
                        <span className="font-semibold">
                          {eng.spend_gbp.toLocaleString("en-GB", {
                            style: "currency",
                            currency: "GBP",
                            maximumFractionDigits: 0,
                          })}
                        </span>
                      </p>
                    )}
                    {eng.co2e_tonnes != null && eng.co2e_tonnes > 0 && (
                      <p className="text-xs text-muted">
                        CO2e: <span className="font-semibold">{eng.co2e_tonnes.toFixed(1)} t</span>
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6 text-center">
            <p className="text-sm text-muted">
              This supplier has not appeared in any engagements yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
