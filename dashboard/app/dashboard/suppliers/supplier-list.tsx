"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type {
  SupplierListItem,
  AdminSupplierFilters,
  CompaniesHouseResult,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreBadgeClass(score: number): string {
  if (score >= 70) return "bg-emerald-100 text-emerald-800";
  if (score >= 40) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}

function statusBadgeClass(status: string): string {
  const s = status?.toLowerCase();
  if (s === "active") return "bg-emerald-100 text-emerald-800";
  if (s === "dissolved") return "bg-red-100 text-red-800";
  return "bg-gray-100 text-gray-600";
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function SupplierList() {
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  /* ---- state ---- */
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [searchText, setSearchText] = useState(searchParams.get("q") || "");
  const [riskLevel, setRiskLevel] = useState(searchParams.get("risk_level") || "");
  const [minScore, setMinScore] = useState(searchParams.get("min_score") || "");
  const [maxScore, setMaxScore] = useState(searchParams.get("max_score") || "");
  const [sector, setSector] = useState(searchParams.get("sector") || "");
  const [enrichmentStatus, setEnrichmentStatus] = useState(searchParams.get("enrichment_status") || "");
  const [analysedAfter, setAnalysedAfter] = useState(searchParams.get("analysed_after") || "");
  const [analysedBefore, setAnalysedBefore] = useState(searchParams.get("analysed_before") || "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") || "name");

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [enrichingIds, setEnrichingIds] = useState<Set<number>>(new Set());

  /* Companies House */
  const [showCH, setShowCH] = useState(false);
  const [chResults, setCHResults] = useState<CompaniesHouseResult[]>([]);
  const [chLoading, setCHLoading] = useState(false);
  const [addingCH, setAddingCH] = useState<Set<string>>(new Set());

  /* Streaming enrichment progress */
  const [enrichActive, setEnrichActive] = useState(false);
  const [enrichSupplierName, setEnrichSupplierName] = useState("");
  const [enrichProgress, setEnrichProgress] = useState("");
  const [enrichDetail, setEnrichDetail] = useState("");
  const [enrichCounts, setEnrichCounts] = useState({ current: 0, total: 0 });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ---- API helper ---- */
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

  /* ---- build query string from current filters ---- */
  const buildQuery = useCallback(() => {
    const params = new URLSearchParams();
    if (searchText) params.set("q", searchText);
    if (riskLevel) params.set("risk_level", riskLevel);
    if (minScore) params.set("min_score", minScore);
    if (maxScore) params.set("max_score", maxScore);
    if (sector) params.set("sector", sector);
    if (enrichmentStatus) params.set("enrichment_status", enrichmentStatus);
    if (analysedAfter) params.set("analysed_after", analysedAfter);
    if (analysedBefore) params.set("analysed_before", analysedBefore);
    if (sortBy && sortBy !== "name") params.set("sort_by", sortBy);
    return params.toString();
  }, [searchText, riskLevel, minScore, maxScore, sector, enrichmentStatus, analysedAfter, analysedBefore, sortBy]);

  /* ---- fetch suppliers ---- */
  const fetchSuppliers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = buildQuery();
      const data = await apiFetch(`/suppliers${qs ? `?${qs}` : ""}`);
      setSuppliers(data.suppliers ?? data);
      setTotal(data.total ?? (data.suppliers ?? data).length);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load suppliers");
    } finally {
      setLoading(false);
    }
  }, [apiFetch, buildQuery]);

  /* ---- sync URL params ---- */
  const syncURL = useCallback(() => {
    const qs = buildQuery();
    router.replace(`/dashboard/suppliers${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [buildQuery, router]);

  /* ---- debounced search ---- */
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      syncURL();
      fetchSuppliers();
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);

  /* ---- refetch when filters (non-search) change ---- */
  useEffect(() => {
    syncURL();
    fetchSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [riskLevel, minScore, maxScore, sector, enrichmentStatus, analysedAfter, analysedBefore, sortBy]);

  /* ---- Companies House search ---- */
  const searchCompaniesHouse = async () => {
    if (!searchText.trim()) return;
    setShowCH(true);
    setCHLoading(true);
    setCHResults([]);
    try {
      const data = await apiFetch(
        `/suppliers/search/companies-house?q=${encodeURIComponent(searchText.trim())}`,
      );
      setCHResults(data.results ?? data);
    } catch (e) {
      setCHResults([]);
      setError(e instanceof Error ? e.message : "Companies House search failed");
    } finally {
      setCHLoading(false);
    }
  };

  /* ---- Streaming enrichment (shared by add-from-CH and re-run) ---- */
  const streamEnrich = useCallback(
    async (supplierId: number, supplierName: string) => {
      setEnrichActive(true);
      setEnrichSupplierName(supplierName);
      setEnrichProgress("Starting analysis...");
      setEnrichDetail("");
      setEnrichCounts({ current: 0, total: 0 });

      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/api/suppliers/${supplierId}/enrich/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `API error ${res.status}`);
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
                setEnrichProgress(`Done — ${msg.findings_generated} findings generated`);
                setEnrichDetail("");
              }
            } catch {
              // skip unparseable lines
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Analysis failed");
      } finally {
        setEnrichActive(false);
      }
    },
    [getToken],
  );

  /* ---- Add from Companies House ---- */
  const addFromCH = async (companyNumber: string, companyName: string) => {
    setAddingCH((prev) => new Set(prev).add(companyNumber));
    try {
      const created = await apiFetch("/suppliers/from-companies-house", {
        method: "POST",
        body: JSON.stringify({ company_number: companyNumber, company_name: companyName, enrich: false }),
      });
      setShowCH(false);
      setCHResults([]);
      await streamEnrich(created.id, created.name || companyName);
      await fetchSuppliers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add supplier");
    } finally {
      setAddingCH((prev) => {
        const next = new Set(prev);
        next.delete(companyNumber);
        return next;
      });
    }
  };

  /* ---- Rerun enrichment ---- */
  const rerunEnrichment = async (id: number, name: string) => {
    setEnrichingIds((prev) => new Set(prev).add(id));
    try {
      await streamEnrich(id, name);
      await fetchSuppliers();
    } finally {
      setEnrichingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  /* ------------------------------------------------------------------ */
  /*  Render                                                             */
  /* ------------------------------------------------------------------ */

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {enrichActive && (
        <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface rounded-2xl border border-[#E5E5E0] shadow-xl max-w-md w-full p-8 flex flex-col items-center text-center">
            <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
            <h3 className="text-sm font-semibold mt-4">Running Analysis</h3>
            {enrichSupplierName && (
              <p className="text-xs text-muted mt-1">{enrichSupplierName}</p>
            )}
            <p className="text-sm font-semibold mt-4">{enrichProgress}</p>
            {enrichDetail && (
              <p className="text-teal text-sm mt-1 font-medium">{enrichDetail}</p>
            )}
            {enrichCounts.total > 0 && (
              <div className="w-full mt-4">
                <div className="w-full h-2 bg-[#E5E5E0] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-teal rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.round((enrichCounts.current / enrichCounts.total) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-[11px] text-muted mt-1 text-center">
                  Layer {enrichCounts.current}/{enrichCounts.total}
                </p>
              </div>
            )}
            <p className="text-muted text-[11px] mt-4 max-w-xs">
              Checking Companies House, Environment Agency, HSE, and 50+ other public databases.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Suppliers</h1>
        <p className="text-muted text-sm mt-0.5">
          {total > 0 ? `${total} supplier${total !== 1 ? "s" : ""}` : "Search or browse all suppliers"}
        </p>
      </div>

      {/* Search bar */}
      <div className="bg-surface rounded-xl border border-[#E5E5E0] p-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search by name or CH number..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-[#E5E5E0] bg-paper text-sm outline-none focus:border-teal transition-colors"
            />
          </div>
          <button
            onClick={searchCompaniesHouse}
            disabled={!searchText.trim()}
            className="px-4 py-2.5 rounded-lg text-xs font-semibold border border-[#E5E5E0] text-muted hover:border-teal hover:text-teal transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            Search Companies House
          </button>
        </div>

        {/* Companies House results */}
        {showCH && (
          <div className="border border-[#E5E5E0] rounded-lg overflow-hidden">
            <div className="flex items-center justify-between bg-paper px-4 py-2">
              <span className="text-xs font-semibold uppercase tracking-[0.5px] text-muted">
                Companies House Results
              </span>
              <button
                onClick={() => { setShowCH(false); setCHResults([]); }}
                className="text-muted hover:text-slate text-xs"
              >
                Close
              </button>
            </div>
            {chLoading ? (
              <div className="p-6 text-center">
                <div className="inline-block w-5 h-5 rounded-full border-2 border-teal/30 border-t-teal animate-spin" />
                <p className="text-muted text-xs mt-2">Searching Companies House...</p>
              </div>
            ) : chResults.length === 0 ? (
              <div className="p-6 text-center text-muted text-sm">No results found.</div>
            ) : (
              <div className="divide-y divide-[#F0F0EB]">
                {chResults.map((r) => (
                  <div key={r.ch_number} className="px-4 py-3 flex items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{r.name}</p>
                      <p className="text-xs text-muted mt-0.5">
                        {[r.ch_number, r.status, r.address].filter(Boolean).join(" · ")}
                      </p>
                    </div>
                    <button
                      onClick={() => addFromCH(r.ch_number, r.name)}
                      disabled={addingCH.has(r.ch_number)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal text-white hover:opacity-90 transition-opacity disabled:opacity-50 whitespace-nowrap"
                    >
                      {addingCH.has(r.ch_number) ? (
                        <span className="flex items-center gap-1.5">
                          <span className="inline-block w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                          Adding...
                        </span>
                      ) : (
                        "Run analysis & add"
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter bar */}
      <div className="bg-surface rounded-xl border border-[#E5E5E0] p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Risk level */}
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted block mb-1">
              Risk Level
            </label>
            <select
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
              className="w-full px-2.5 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
            >
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Score range */}
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted block mb-1">
              Score Range
            </label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={0}
                max={100}
                value={minScore}
                onChange={(e) => setMinScore(e.target.value)}
                placeholder="Min"
                className="w-full px-2 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
              />
              <span className="text-muted text-xs">-</span>
              <input
                type="number"
                min={0}
                max={100}
                value={maxScore}
                onChange={(e) => setMaxScore(e.target.value)}
                placeholder="Max"
                className="w-full px-2 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
              />
            </div>
          </div>

          {/* Sector */}
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted block mb-1">
              Sector
            </label>
            <input
              type="text"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="e.g. Energy"
              className="w-full px-2.5 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
            />
          </div>

          {/* Enrichment status */}
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted block mb-1">
              Enrichment
            </label>
            <select
              value={enrichmentStatus}
              onChange={(e) => setEnrichmentStatus(e.target.value)}
              className="w-full px-2.5 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
            >
              <option value="">All</option>
              <option value="enriched">Enriched</option>
              <option value="not_enriched">Not enriched</option>
            </select>
          </div>

          {/* Last analysed date range */}
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted block mb-1">
              Analysed After
            </label>
            <input
              type="date"
              value={analysedAfter}
              onChange={(e) => setAnalysedAfter(e.target.value)}
              className="w-full px-2.5 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
            />
          </div>

          <div>
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted block mb-1">
              Analysed Before
            </label>
            <input
              type="date"
              value={analysedBefore}
              onChange={(e) => setAnalysedBefore(e.target.value)}
              className="w-full px-2.5 py-2 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
            />
          </div>
        </div>

        {/* Sort + clear */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#F0F0EB]">
          <div className="flex items-center gap-2">
            <label className="text-[10px] font-semibold uppercase tracking-[0.5px] text-muted">Sort</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-[#E5E5E0] bg-paper text-xs outline-none focus:border-teal"
            >
              <option value="name">Alphabetical</option>
              <option value="score">Score</option>
              <option value="last_analysed">Last analysed</option>
              <option value="risk">Risk</option>
            </select>
          </div>
          <button
            onClick={() => {
              setSearchText("");
              setRiskLevel("");
              setMinScore("");
              setMaxScore("");
              setSector("");
              setEnrichmentStatus("");
              setAnalysedAfter("");
              setAnalysedBefore("");
              setSortBy("name");
            }}
            className="text-xs text-muted hover:text-teal transition-colors"
          >
            Clear filters
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-4 text-center">
          <p className="text-red-600 text-sm">{error}</p>
          <p className="text-muted text-xs mt-1">Check that the API is running and try refreshing.</p>
        </div>
      )}

      {/* Supplier rows */}
      {loading ? (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <div className="inline-block w-5 h-5 rounded-full border-2 border-teal/30 border-t-teal animate-spin" />
          <p className="text-muted text-xs mt-2">Loading suppliers...</p>
        </div>
      ) : suppliers.length === 0 && !error ? (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm">No suppliers found. Try a different search or add from Companies House.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {suppliers.map((s) => (
            <SupplierRow
              key={s.id}
              supplier={s}
              expanded={expandedId === s.id}
              onToggle={() => setExpandedId(expandedId === s.id ? null : s.id)}
              enriching={enrichingIds.has(s.id)}
              onRerunEnrichment={() => rerunEnrichment(s.id, s.name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Supplier row                                                       */
/* ------------------------------------------------------------------ */

function SupplierRow({
  supplier: s,
  expanded,
  onToggle,
  enriching,
  onRerunEnrichment,
}: {
  supplier: SupplierListItem;
  expanded: boolean;
  onToggle: () => void;
  enriching: boolean;
  onRerunEnrichment: () => void;
}) {
  const analysedDate = s.last_analysed_at
    ? new Date(s.last_analysed_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div className="bg-surface rounded-xl border border-[#E5E5E0] hover:border-teal/30 transition-all">
      {/* Main row */}
      <div className="p-4 flex items-center gap-4">
        {/* Name + CH */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Link
              href={`/dashboard/suppliers/${s.id}`}
              className="text-sm font-semibold hover:text-teal transition-colors truncate"
            >
              {s.name}
            </Link>
            {s.critical_flag && (
              <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" title="Critical" />
            )}
          </div>
          <p className="text-xs text-muted mt-0.5 truncate">
            {s.ch_number} &middot; {s.sector || "No sector"}
          </p>
        </div>

        {/* Status badge */}
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-[0.5px] flex-shrink-0 ${statusBadgeClass(s.status)}`}
        >
          {s.status}
        </span>

        {/* Score badge */}
        <span
          className={`px-2.5 py-1 rounded-lg text-xs font-bold tabular-nums flex-shrink-0 ${scoreBadgeClass(s.hemera_score)}`}
        >
          {s.hemera_score}
        </span>

        {/* Confidence */}
        <span className="text-[10px] text-muted flex-shrink-0 w-16 text-center">
          {s.confidence}
        </span>

        {/* Last analysed */}
        <span className="text-xs flex-shrink-0 w-24 text-right tabular-nums">
          {analysedDate ? (
            <span className="text-slate">{analysedDate}</span>
          ) : (
            <span className="text-muted italic">Not analysed</span>
          )}
        </span>

        {/* Engagement count */}
        <span className="text-xs text-muted flex-shrink-0 w-10 text-center tabular-nums" title="Engagements">
          {s.engagement_count}
        </span>

        {/* Expand chevron */}
        <button
          onClick={onToggle}
          className="p-1 text-muted hover:text-teal transition-colors flex-shrink-0"
          title={expanded ? "Collapse" : "Expand"}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>

      {/* Expanded quick preview */}
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-[#F0F0EB] mt-0">
          <div className="pt-3 flex items-center gap-3">
            <Link
              href={`/dashboard/suppliers/${s.id}`}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-teal text-white hover:opacity-90 transition-opacity"
            >
              View full profile
            </Link>
            <button
              onClick={onRerunEnrichment}
              disabled={enriching}
              className="px-4 py-2 rounded-lg text-xs font-semibold border border-[#E5E5E0] text-muted hover:border-teal hover:text-teal transition-colors disabled:opacity-50"
            >
              {enriching ? (
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-3 h-3 rounded-full border-2 border-teal/30 border-t-teal animate-spin" />
                  Enriching...
                </span>
              ) : (
                "Rerun analysis"
              )}
            </button>
            {enriching && (
              <span className="text-[10px] text-muted">Analysis in progress. This may take a few minutes.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
