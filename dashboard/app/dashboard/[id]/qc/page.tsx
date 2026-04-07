"use client";

import { useAuth } from "@clerk/nextjs";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const QC_CHECKS = [
  { key: "classification", label: "Classification" },
  { key: "emission_factor", label: "Emission Factor" },
  { key: "arithmetic", label: "Arithmetic" },
  { key: "supplier_match", label: "Supplier Match" },
  { key: "pedigree", label: "Pedigree" },
] as const;

type CheckKey = (typeof QC_CHECKS)[number]["key"];

interface SampledTransaction {
  id: number;
  description: string;
  supplier: string;
  amount_gbp: number;
  scope: number;
  category: string;
  co2e_kg: number;
  gsd: number;
  ef_level: number;
  ef_source: string;
}

interface QCResult {
  transaction_id: number;
  checks: Record<CheckKey, boolean>;
}

interface SubmitResponse {
  status: string;
  error_rate: number;
  total_checked: number;
  failed_checks: number;
}

type PageState =
  | "loading_status"
  | "uploaded"
  | "triggering"
  | "processing"
  | "idle"
  | "loading"
  | "reviewing"
  | "submitting"
  | "submitted"
  | "qc_passed"
  | "error";

export default function QCPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [pageState, setPageState] = useState<PageState>("loading_status");
  const [errorMsg, setErrorMsg] = useState("");
  const [transactions, setTransactions] = useState<SampledTransaction[]>([]);
  const [results, setResults] = useState<Record<number, Record<CheckKey, boolean>>>({});
  const [submitResponse, setSubmitResponse] = useState<SubmitResponse | null>(null);

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

  // Fetch engagement status on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await apiFetch<{ status: string }>(`/engagements/${id}`);
        const status = data.status;
        if (status === "uploaded") {
          setPageState("uploaded");
        } else if (status === "processing") {
          setPageState("processing");
        } else if (status === "delivered") {
          setPageState("idle");
        } else if (status === "qc_passed") {
          setPageState("qc_passed");
        } else {
          setPageState("idle");
        }
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load engagement");
        setPageState("error");
      }
    };
    fetchStatus();
  }, [apiFetch, id]);

  const triggerProcessing = useCallback(async () => {
    setPageState("triggering");
    setErrorMsg("");
    try {
      await apiFetch(`/engagements/${id}/process`, { method: "POST" });
      setPageState("processing");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to start processing");
      setPageState("error");
    }
  }, [apiFetch, id]);

  const generateSample = useCallback(async () => {
    setPageState("loading");
    setErrorMsg("");
    try {
      const data = await apiFetch<{ transactions: SampledTransaction[] }>(
        `/engagements/${id}/qc/generate`,
        { method: "POST" }
      );
      const txns = data.transactions ?? [];
      setTransactions(txns);
      // Initialize all checks as true (passing) by default
      const initial: Record<number, Record<CheckKey, boolean>> = {};
      txns.forEach((t) => {
        initial[t.id] = {
          classification: true,
          emission_factor: true,
          arithmetic: true,
          supplier_match: true,
          pedigree: true,
        };
      });
      setResults(initial);
      setPageState("reviewing");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to generate sample");
      setPageState("error");
    }
  }, [apiFetch, id]);

  const toggleCheck = (txnId: number, checkKey: CheckKey) => {
    setResults((prev) => ({
      ...prev,
      [txnId]: {
        ...prev[txnId],
        [checkKey]: !prev[txnId][checkKey],
      },
    }));
  };

  const submitReview = useCallback(async () => {
    setPageState("submitting");
    try {
      const qcResults: QCResult[] = transactions.map((t) => ({
        transaction_id: t.id,
        checks: results[t.id],
      }));
      const data = await apiFetch<SubmitResponse>(`/engagements/${id}/qc/submit`, {
        method: "POST",
        body: JSON.stringify({ results: qcResults }),
      });
      setSubmitResponse(data);
      setPageState("submitted");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Submission failed");
      setPageState("error");
    }
  }, [apiFetch, id, transactions, results]);

  const totalFailed = Object.values(results).reduce((sum, checks) => {
    return sum + Object.values(checks).filter((v) => !v).length;
  }, 0);

  if (pageState === "loading_status") {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">QC Review</h1>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin mx-auto" />
          <p className="text-muted text-sm mt-3">Loading…</p>
        </div>
      </div>
    );
  }

  if (pageState === "uploaded" || pageState === "triggering") {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">QC Review</h1>
          <p className="text-muted text-sm mt-0.5">Process this engagement to begin QC.</p>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center space-y-4">
          <p className="text-muted text-sm">
            This engagement has been uploaded and is ready to process. Click below to classify
            transactions and calculate the carbon footprint.
          </p>
          <button
            onClick={triggerProcessing}
            disabled={pageState === "triggering"}
            className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {pageState === "triggering" ? "Starting…" : "Start Processing"}
          </button>
        </div>
      </div>
    );
  }

  if (pageState === "processing") {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">QC Review</h1>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center space-y-4">
          <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin mx-auto" />
          <p className="font-medium">Processing…</p>
          <p className="text-muted text-sm">
            Classifying transactions and calculating carbon footprint. This may take a few minutes.
          </p>
        </div>
      </div>
    );
  }

  if (pageState === "qc_passed") {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">QC Review</h1>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-[#D1FAE5] flex items-center justify-center mx-auto">
            <svg className="w-7 h-7 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold">QC Complete</h3>
          <p className="text-muted text-sm">
            This engagement has passed quality control and is approved.
          </p>
          <Badge variant="green">Approved</Badge>
        </div>
      </div>
    );
  }

  if (pageState === "submitted" && submitResponse) {
    const errorRate = submitResponse.error_rate * 100;
    const statusVariant =
      errorRate === 0 ? "green" : errorRate < 10 ? "amber" : "red";

    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">QC Review</h1>
          <p className="text-muted text-sm mt-0.5">Review complete</p>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-[#D1FAE5] flex items-center justify-center mx-auto">
            <svg className="w-7 h-7 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold">QC Submitted</h3>
          <div className="grid grid-cols-3 gap-4 max-w-xs mx-auto">
            <div className="bg-paper rounded-lg p-3 text-center">
              <div className="text-2xl font-bold tabular-nums">{submitResponse.total_checked}</div>
              <div className="text-[11px] text-muted mt-0.5">Checked</div>
            </div>
            <div className="bg-paper rounded-lg p-3 text-center">
              <div className="text-2xl font-bold tabular-nums text-error">{submitResponse.failed_checks}</div>
              <div className="text-[11px] text-muted mt-0.5">Failed</div>
            </div>
            <div className="bg-paper rounded-lg p-3 text-center">
              <div className="text-2xl font-bold tabular-nums">{errorRate.toFixed(1)}%</div>
              <div className="text-[11px] text-muted mt-0.5">Error Rate</div>
            </div>
          </div>
          <div className="mt-2">
            <Badge variant={statusVariant}>{submitResponse.status}</Badge>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">QC Review</h1>
        <p className="text-muted text-sm mt-0.5">
          Sample and review transactions for quality control.
        </p>
      </div>

      {pageState === "idle" && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm mb-4">
            Generate a random sample of transactions to review for classification,
            emission factors, and data quality.
          </p>
          <button
            onClick={generateSample}
            className="px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            Generate Sample
          </button>
        </div>
      )}

      {pageState === "loading" && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin mx-auto" />
          <p className="text-muted text-sm mt-3">Generating sample…</p>
        </div>
      )}

      {pageState === "error" && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-error text-sm mb-4">{errorMsg}</p>
          <button
            onClick={() => setPageState("idle")}
            className="px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            Try Again
          </button>
        </div>
      )}

      {(pageState === "reviewing" || pageState === "submitting") && (
        <>
          <div className="space-y-4">
            {transactions.map((txn) => {
              const txnResults = results[txn.id] ?? {};
              const failedCount = Object.values(txnResults).filter((v) => !v).length;

              return (
                <div key={txn.id} className="bg-surface rounded-lg border border-[#E5E5E0] p-5">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div className="min-w-0">
                      <div className="font-medium truncate">{txn.description}</div>
                      <div className="text-muted text-xs mt-0.5">
                        {txn.supplier} · £{txn.amount_gbp.toFixed(2)} · {txn.category}
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <div className="text-sm font-semibold tabular-nums">
                        {(txn.co2e_kg / 1000).toFixed(3)} tCO₂e
                      </div>
                      <div className="text-[11px] text-muted">Scope {txn.scope}</div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {QC_CHECKS.map(({ key, label }) => {
                      const passing = txnResults[key] ?? true;
                      return (
                        <button
                          key={key}
                          onClick={() => toggleCheck(txn.id, key)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                            passing
                              ? "bg-[#D1FAE5] text-[#065F46] border-[#A7F3D0] hover:bg-[#BBFCE4]"
                              : "bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5] hover:bg-[#FECACA]"
                          }`}
                        >
                          {passing ? "✓" : "✗"} {label}
                        </button>
                      );
                    })}
                  </div>
                  {/* suppress unused variable warning */}
                  {failedCount > 0 && null}
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between bg-surface rounded-lg border border-[#E5E5E0] p-4">
            <div className="text-sm text-muted">
              {totalFailed > 0 ? (
                <span className="text-error font-medium">{totalFailed} check{totalFailed !== 1 ? "s" : ""} flagged</span>
              ) : (
                <span className="text-success font-medium">All checks passing</span>
              )}
              {" "}across {transactions.length} transactions
            </div>
            <button
              onClick={submitReview}
              disabled={pageState === "submitting"}
              className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {pageState === "submitting" ? "Submitting…" : "Submit QC Review"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
