"use client";

import { useAuth } from "@clerk/nextjs";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const HARD_GATE_THRESHOLD = 0.05;

interface StrataBreakdown {
  by_scope: Record<string, number>;
  by_ef_level: Record<string, number>;
  high_value_sampled: number;
  low_confidence_sampled: number;
}

interface SampleData {
  engagement_id: number;
  sample_size: number;
  population_size: number;
  confidence_level: number;
  acceptable_error_rate: number;
  strata_breakdown: StrataBreakdown;
}

interface QCStatus {
  status: string;
  sample_size: number;
  reviewed_count: number;
  pass_count: number;
  fail_count: number;
  current_error_rate: number;
  hard_gate_threshold: number;
}

interface EngagementInfo {
  id: number;
  org_name: string;
  status: string;
  transaction_count: number;
  total_co2e: number;
  created_at: string;
}

export default function SamplingReportPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [engagement, setEngagement] = useState<EngagementInfo | null>(null);
  const [sampleData, setSampleData] = useState<SampleData | null>(null);
  const [qcStatus, setQCStatus] = useState<QCStatus | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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

  useEffect(() => {
    const load = async () => {
      try {
        const [eng, sample, status] = await Promise.all([
          apiFetch<EngagementInfo>(`/engagements/${id}`),
          apiFetch<SampleData>(`/engagements/${id}/qc/generate`, { method: "POST" }),
          apiFetch<QCStatus>(`/engagements/${id}/qc`),
        ]);
        setEngagement(eng);
        setSampleData(sample);
        setQCStatus(status);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load report data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [apiFetch, id]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center">
        <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin mx-auto" />
        <p className="text-muted text-sm mt-3">Loading report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center">
        <p className="text-error text-sm">{error}</p>
      </div>
    );
  }

  if (!sampleData || !engagement) return null;

  const { sample_size, population_size, confidence_level, acceptable_error_rate, strata_breakdown } = sampleData;
  const samplingRate = population_size > 0 ? ((sample_size / population_size) * 100).toFixed(1) : "0";
  const scopeEntries = Object.entries(strata_breakdown.by_scope).sort(([a], [b]) => a.localeCompare(b));
  const efLevelEntries = Object.entries(strata_breakdown.by_ef_level).sort(([a], [b]) => a.localeCompare(b));
  const reportDate = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const hasQCResults = qcStatus && qcStatus.status !== "not_started";

  return (
    <>
      {/* Print button — hidden when printing */}
      <div className="print:hidden max-w-3xl mx-auto pt-6 flex justify-end gap-3">
        <button
          onClick={() => window.print()}
          className="px-4 py-2 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Print / Save PDF
        </button>
      </div>

      {/* Report — single A4 page */}
      <div className="max-w-3xl mx-auto bg-white print:bg-white print:shadow-none print:m-0 print:p-0 rounded-xl shadow-sm border border-[#E5E5E0] print:border-0 my-6 print:my-0">
        <div className="p-8 print:p-6 space-y-6">

          {/* Header */}
          <div className="flex items-start justify-between border-b border-[#E5E5E0] pb-4">
            <div>
              <div className="text-teal text-[10px] font-bold uppercase tracking-[3px]">Hemera</div>
              <h1 className="text-xl font-bold mt-1">Stratified Sampling Report</h1>
              <p className="text-muted text-xs mt-0.5">
                ISO 19011 compliant quality control sampling
              </p>
            </div>
            <div className="text-right text-xs text-muted">
              <div className="font-semibold text-slate">{engagement.org_name}</div>
              <div>Engagement #{engagement.id}</div>
              <div>{reportDate}</div>
            </div>
          </div>

          {/* Key figures */}
          <div className="grid grid-cols-5 gap-3">
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-xl font-bold tabular-nums">{population_size.toLocaleString()}</div>
              <div className="text-[10px] text-muted mt-0.5">Population</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-xl font-bold tabular-nums text-teal">{sample_size}</div>
              <div className="text-[10px] text-muted mt-0.5">Sample Size</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-xl font-bold tabular-nums">{samplingRate}%</div>
              <div className="text-[10px] text-muted mt-0.5">Sampling Rate</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-xl font-bold tabular-nums">{(confidence_level * 100).toFixed(0)}%</div>
              <div className="text-[10px] text-muted mt-0.5">Confidence</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-xl font-bold tabular-nums">{(acceptable_error_rate * 100).toFixed(0)}%</div>
              <div className="text-[10px] text-muted mt-0.5">Max Error</div>
            </div>
          </div>

          {/* Methodology */}
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted mb-2">Methodology</h2>
            <div className="text-[11px] leading-relaxed space-y-1.5">
              <p>
                Sample size calculated using the ISO 19011 formula:
                <span className="font-mono text-[10px] ml-1">
                  n = N&middot;Z&sup2;&middot;P(1-P) / [E&sup2;(N-1) + Z&sup2;&middot;P(1-P)]
                </span>
                {" "}where Z = 1.96 (95% CI), P = 0.5 (maximum variability), E = {acceptable_error_rate} (acceptable error rate).
              </p>
              <p>
                Transactions are weighted for selection using three risk multipliers (each 2x when triggered):
              </p>
              <div className="grid grid-cols-3 gap-2 mt-1">
                <div className="bg-[#FAFAF7] rounded p-2">
                  <div className="font-semibold text-[10px]">High-Spend</div>
                  <div className="text-muted text-[10px]">Top 10% by absolute value</div>
                </div>
                <div className="bg-[#FAFAF7] rounded p-2">
                  <div className="font-semibold text-[10px]">Low-Confidence</div>
                  <div className="text-muted text-[10px]">Classification method: none/LLM</div>
                </div>
                <div className="bg-[#FAFAF7] rounded p-2">
                  <div className="font-semibold text-[10px]">High-Uncertainty EF</div>
                  <div className="text-muted text-[10px]">Emission factor Level 5-6</div>
                </div>
              </div>
            </div>
          </div>

          {/* Strata breakdown */}
          <div className="grid grid-cols-2 gap-6">
            {/* By scope */}
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted mb-2">Sample by Scope</h2>
              <div className="space-y-1.5">
                {scopeEntries.map(([scope, count]) => (
                  <div key={scope} className="flex items-center justify-between text-xs">
                    <span>Scope {scope}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-28 h-2 bg-[#E5E5E0] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal rounded-full"
                          style={{ width: `${(count / sample_size) * 100}%` }}
                        />
                      </div>
                      <span className="tabular-nums font-medium w-8 text-right">{count}</span>
                      <span className="tabular-nums text-muted w-10 text-right text-[10px]">
                        {((count / sample_size) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* By EF level */}
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted mb-2">Sample by EF Level</h2>
              <div className="space-y-1.5">
                {efLevelEntries.map(([level, count]) => (
                  <div key={level} className="flex items-center justify-between text-xs">
                    <span>{level}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-28 h-2 bg-[#E5E5E0] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#6366F1] rounded-full"
                          style={{ width: `${(count / sample_size) * 100}%` }}
                        />
                      </div>
                      <span className="tabular-nums font-medium w-8 text-right">{count}</span>
                      <span className="tabular-nums text-muted w-10 text-right text-[10px]">
                        {((count / sample_size) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Risk flags */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-lg font-bold tabular-nums">{strata_breakdown.high_value_sampled}</div>
              <div className="text-[10px] text-muted mt-0.5">High-Value Transactions Sampled</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-lg font-bold tabular-nums">{strata_breakdown.low_confidence_sampled}</div>
              <div className="text-[10px] text-muted mt-0.5">Low-Confidence Classifications Sampled</div>
            </div>
          </div>

          {/* QC Result (if available) */}
          {hasQCResults && qcStatus && (
            <div className="border-t border-[#E5E5E0] pt-4">
              <h2 className="text-xs font-semibold uppercase tracking-[0.5px] text-muted mb-2">QC Result</h2>
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold tabular-nums">{qcStatus.reviewed_count}</div>
                  <div className="text-[10px] text-muted mt-0.5">Reviewed</div>
                </div>
                <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold tabular-nums text-[#065F46]">{qcStatus.pass_count}</div>
                  <div className="text-[10px] text-muted mt-0.5">Passed</div>
                </div>
                <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold tabular-nums text-[#991B1B]">{qcStatus.fail_count}</div>
                  <div className="text-[10px] text-muted mt-0.5">Failed</div>
                </div>
                <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
                  <div className={`text-lg font-bold tabular-nums ${qcStatus.current_error_rate <= HARD_GATE_THRESHOLD ? "text-[#065F46]" : "text-[#991B1B]"}`}>
                    {(qcStatus.current_error_rate * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-muted mt-0.5">Error Rate</div>
                </div>
              </div>
              {qcStatus.status === "passed" && (
                <div className="mt-3 flex items-center gap-2 text-xs text-[#065F46] font-semibold">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Hard gate passed — error rate {(qcStatus.current_error_rate * 100).toFixed(1)}% is within {(HARD_GATE_THRESHOLD * 100).toFixed(0)}% threshold
                </div>
              )}
              {qcStatus.status === "failed" && (
                <div className="mt-3 flex items-center gap-2 text-xs text-[#991B1B] font-semibold">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Hard gate failed — error rate {(qcStatus.current_error_rate * 100).toFixed(1)}% exceeds {(HARD_GATE_THRESHOLD * 100).toFixed(0)}% threshold
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="border-t border-[#E5E5E0] pt-3 flex items-center justify-between text-[10px] text-muted">
            <span>Hemera — Supply Chain Carbon Intelligence</span>
            <span>Hard gate threshold: {(HARD_GATE_THRESHOLD * 100).toFixed(0)}% error rate</span>
          </div>
        </div>
      </div>
    </>
  );
}
