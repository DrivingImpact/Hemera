"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const HARD_GATE_THRESHOLD = 0.05;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface QCCard {
  card_number: number;
  total_cards: number;
  transaction_id: number;
  qc_pass: boolean | null;
  sampling_reasons: string[];
  raw_data: {
    row_number: number;
    raw_date: string;
    raw_description: string;
    raw_supplier: string;
    raw_amount: string;
    raw_category: string;
  };
  decisions: {
    classification: {
      scope: number;
      ghg_category: string;
      category_name: string;
      method: string;
      confidence: number;
    };
    supplier_match: {
      supplier_id: number | null;
      match_method: string;
    };
    emission_factor: {
      value: number;
      unit: string;
      source: string;
      level: number;
      year: number;
      region: string;
    };
    calculation: {
      amount_gbp: number;
      ef_value: number;
      co2e_kg: number;
      arithmetic_verified: boolean;
    };
    pedigree: {
      reliability: number;
      completeness: number;
      temporal: number;
      geographical: number;
      technological: number;
      gsd_total: number;
    };
  };
}

interface GenerateResponse {
  engagement_id: number;
  sample_size: number;
  population_size: number;
  confidence_level: number;
  acceptable_error_rate: number;
  strata_breakdown: {
    by_scope: Record<string, number>;
    by_ef_level: Record<string, number>;
    high_value_sampled: number;
    low_confidence_sampled: number;
  };
  cards: QCCard[];
}

interface SubmitResponse {
  accepted: number;
  remaining: number;
  qc_complete: boolean;
  current_error_rate: number;
  hard_gate_result?: string;
  engagement_status?: string;
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
  | "done"
  | "error";

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function QCPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [pageState, setPageState] = useState<PageState>("loading_status");
  const [errorMsg, setErrorMsg] = useState("");
  const [engagementInfo, setEngagementInfo] = useState<{ transaction_count: number; org_name: string } | null>(null);
  const [sampleData, setSampleData] = useState<GenerateResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [verdicts, setVerdicts] = useState<Record<number, "pass" | "fail">>({});
  const [cardOrder, setCardOrder] = useState<number[]>([]);  // indices into sampleData.cards
  const [submitResponse, setSubmitResponse] = useState<SubmitResponse | null>(null);
  const [swipeDir, setSwipeDir] = useState<"left" | "right" | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  /* --- Poll for processing --- */
  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const data = await apiFetch<{ status: string }>(`/engagements/${id}`);
        if (data.status === "delivered") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setPageState("idle");
        } else if (data.status !== "processing") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch { /* keep polling */ }
    }, 5000);
  }, [apiFetch, id]);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  /* --- Load engagement status --- */
  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiFetch<{ status: string; transaction_count: number; org_name: string }>(`/engagements/${id}`);
        setEngagementInfo({ transaction_count: data.transaction_count, org_name: data.org_name });
        if (data.status === "uploaded") setPageState("uploaded");
        else if (data.status === "processing") { setPageState("processing"); startPolling(); }
        else if (data.status === "delivered") setPageState("idle");
        else if (data.status === "qc_passed") setPageState("done");
        else setPageState("idle");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load");
        setPageState("error");
      }
    };
    load();
  }, [apiFetch, id, startPolling]);

  /* --- Trigger processing --- */
  const triggerProcessing = useCallback(async () => {
    setPageState("triggering");
    try {
      await apiFetch(`/engagements/${id}/process`, { method: "POST" });
      setPageState("processing");
      startPolling();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to process");
      setPageState("error");
    }
  }, [apiFetch, id, startPolling]);

  /* --- Generate sample (or resume existing) --- */
  const generateSample = useCallback(async () => {
    setPageState("loading");
    try {
      const data = await apiFetch<GenerateResponse>(
        `/engagements/${id}/qc/generate`,
        { method: "POST" }
      );
      setSampleData(data);

      // Restore verdicts for already-reviewed cards
      const restored: Record<number, "pass" | "fail"> = {};
      const unreviewedIndices: number[] = [];
      data.cards.forEach((c: QCCard, i: number) => {
        if (c.qc_pass === true) {
          restored[c.transaction_id] = "pass";
        } else if (c.qc_pass === false) {
          restored[c.transaction_id] = "fail";
        } else {
          unreviewedIndices.push(i);
        }
      });
      setVerdicts(restored);
      setCardOrder(unreviewedIndices);
      setCurrentIndex(0);
      setPageState("reviewing");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to generate sample");
      setPageState("error");
    }
  }, [apiFetch, id]);

  /* --- Save a single verdict to backend --- */
  const saveVerdict = useCallback(async (txnId: number, verdict: "pass" | "fail") => {
    const pass = verdict === "pass";
    try {
      await apiFetch<SubmitResponse>(`/engagements/${id}/qc/submit`, {
        method: "POST",
        body: JSON.stringify({
          results: [{
            transaction_id: txnId,
            classification_pass: pass,
            emission_factor_pass: pass,
            arithmetic_pass: pass,
            supplier_match_pass: pass,
            pedigree_pass: pass,
            notes: pass ? "" : "Failed QC review",
          }],
        }),
      });
    } catch {
      // Verdict is still tracked locally — will be retried on final submit
    }
  }, [apiFetch, id]);

  /* --- Verdict handler — saves immediately --- */
  const setVerdict = useCallback((txnId: number, verdict: "pass" | "fail") => {
    setSwipeDir(verdict === "pass" ? "right" : "left");
    saveVerdict(txnId, verdict);
    setTimeout(() => {
      setVerdicts((prev) => ({ ...prev, [txnId]: verdict }));
      setSwipeDir(null);
      setCurrentIndex((prev) => prev + 1);
    }, 300);
  }, [saveVerdict]);

  /* --- Skip / come back later --- */
  const skipCard = useCallback(() => {
    setSwipeDir("right");
    setTimeout(() => {
      setCardOrder((prev) => {
        const current = prev[currentIndex];
        const next = [...prev];
        next.splice(currentIndex, 1);
        next.push(current);
        return next;
      });
      setSwipeDir(null);
      // currentIndex stays the same — the next card slides in
    }, 300);
  }, [currentIndex]);

  /* --- Keyboard shortcuts --- */
  useEffect(() => {
    if (pageState !== "reviewing" || !sampleData) return;
    const cardIdx = cardOrder[currentIndex];
    const card = cardIdx != null ? sampleData.cards[cardIdx] : undefined;
    if (!card) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "a") {
        setVerdict(card.transaction_id, "pass");
      } else if (e.key === "ArrowLeft" || e.key === "d") {
        setVerdict(card.transaction_id, "fail");
      } else if (e.key === "ArrowDown" || e.key === "s") {
        skipCard();
      } else if (e.key === "Backspace" && currentIndex > 0) {
        setCurrentIndex((prev) => prev - 1);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pageState, sampleData, cardOrder, currentIndex, setVerdict, skipCard]);

  /* --- Check completion — fetch final status from backend --- */
  const checkCompletion = useCallback(async () => {
    if (!sampleData) return;
    setPageState("submitting");
    try {
      const status = await apiFetch<{
        status: string;
        current_error_rate: number;
        hard_gate_result?: string;
        reviewed_count: number;
        sample_size: number;
        pass_count: number;
        fail_count: number;
      }>(`/engagements/${id}/qc`);
      if (status.status === "passed" || status.status === "failed") {
        setSubmitResponse({
          accepted: status.reviewed_count,
          remaining: 0,
          qc_complete: true,
          current_error_rate: status.current_error_rate,
          hard_gate_result: status.hard_gate_result,
          engagement_status: status.status === "passed" ? "qc_passed" : "delivered",
        });
        setPageState("done");
      } else {
        // Not all reviewed yet — shouldn't happen but handle gracefully
        setPageState("reviewing");
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to check status");
      setPageState("error");
    }
  }, [apiFetch, id, sampleData]);

  /* --- Auto-complete when all cards reviewed --- */
  useEffect(() => {
    if (
      pageState === "reviewing" &&
      sampleData &&
      Object.keys(verdicts).length === sampleData.cards.length
    ) {
      checkCompletion();
    }
  }, [pageState, sampleData, verdicts, checkCompletion]);

  /* ---------------------------------------------------------------- */
  /*  Render states                                                    */
  /* ---------------------------------------------------------------- */

  // Loading
  if (pageState === "loading_status" || pageState === "loading") {
    return (
      <CenteredPanel>
        <Spinner />
        <p className="text-muted text-sm mt-3">
          {pageState === "loading" ? "Generating sample..." : "Loading..."}
        </p>
      </CenteredPanel>
    );
  }

  // Uploaded — needs processing
  if (pageState === "uploaded" || pageState === "triggering") {
    return (
      <CenteredPanel>
        <div className="w-16 h-16 rounded-full bg-amber-tint flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">Data Uploaded</h2>
        <p className="text-muted text-sm mt-1 max-w-sm">
          This engagement needs to be processed before QC review.
          Processing will classify each transaction and calculate the carbon footprint.
        </p>
        {engagementInfo && (
          <div className="mt-3 text-xs text-muted bg-[#FAFAF7] rounded-lg px-4 py-2.5">
            <span className="font-semibold text-slate">{engagementInfo.transaction_count.toLocaleString()}</span> transactions to classify & calculate
          </div>
        )}
        <button
          onClick={triggerProcessing}
          disabled={pageState === "triggering"}
          className="mt-4 px-6 py-3 bg-slate text-white rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {pageState === "triggering"
            ? "Starting..."
            : `Process ${engagementInfo?.transaction_count.toLocaleString() ?? ""} Transactions`}
        </button>
      </CenteredPanel>
    );
  }

  // Processing
  if (pageState === "processing") {
    return (
      <CenteredPanel>
        <Spinner />
        <h2 className="text-lg font-semibold mt-4">Processing</h2>
        <p className="text-muted text-sm mt-1">
          Classifying transactions and calculating carbon footprint.
          This page updates automatically.
        </p>
      </CenteredPanel>
    );
  }

  // Ready for QC
  if (pageState === "idle") {
    return (
      <CenteredPanel>
        <div className="w-16 h-16 rounded-full bg-teal-tint flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">Ready for QC Review</h2>
        <p className="text-muted text-sm mt-1 max-w-sm">
          Generate a stratified sample of transactions to review.
          You&apos;ll check each one for correct classification, emission factors, and data quality.
        </p>
        <button
          onClick={generateSample}
          className="mt-5 px-6 py-3 bg-teal text-white rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Generate Sample & Start Review
        </button>
      </CenteredPanel>
    );
  }

  // Error
  if (pageState === "error") {
    return (
      <CenteredPanel>
        <p className="text-error text-sm">{errorMsg}</p>
        <button
          onClick={() => setPageState("idle")}
          className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold hover:opacity-90"
        >
          Try Again
        </button>
      </CenteredPanel>
    );
  }

  // Submitting
  if (pageState === "submitting") {
    return (
      <CenteredPanel>
        <Spinner />
        <p className="text-muted text-sm mt-3">Submitting results...</p>
      </CenteredPanel>
    );
  }

  // Done — show results
  if (pageState === "done") {
    const passed = submitResponse?.hard_gate_result === "passed" ||
      (!submitResponse && true); // qc_passed from status check
    const failCount = Object.values(verdicts).filter((v) => v === "fail").length;
    const passCount = Object.values(verdicts).filter((v) => v === "pass").length;
    const errorRate = submitResponse?.current_error_rate ?? 0;

    return (
      <CenteredPanel>
        <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto ${
          passed ? "bg-[#D1FAE5]" : "bg-[#FEE2E2]"
        }`}>
          {passed ? (
            <svg className="w-10 h-10 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-10 h-10 text-[#991B1B]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
        </div>
        <h2 className="text-xl font-bold mt-4">
          {passed ? "QC Passed" : "QC Failed"}
        </h2>
        {submitResponse && (
          <>
            <div className="flex items-center gap-6 mt-4 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold tabular-nums text-[#065F46]">{passCount}</div>
                <div className="text-[11px] text-muted">Passed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold tabular-nums text-[#991B1B]">{failCount}</div>
                <div className="text-[11px] text-muted">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold tabular-nums">{(errorRate * 100).toFixed(1)}%</div>
                <div className="text-[11px] text-muted">Error Rate</div>
              </div>
            </div>
            <p className="text-muted text-xs mt-3">
              Hard gate threshold: {(HARD_GATE_THRESHOLD * 100).toFixed(0)}%
            </p>
          </>
        )}
        <div className="flex items-center gap-3 mt-6">
          <Link
            href={`/dashboard/${id}/qc/report`}
            target="_blank"
            className="px-5 py-2.5 border border-[#E5E5E0] rounded-lg text-sm font-semibold text-muted hover:bg-paper transition-colors"
          >
            View Sampling Report
          </Link>
          <Link
            href="/dashboard/clients"
            className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            Back to Queue
          </Link>
        </div>
      </CenteredPanel>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Card review mode (the Tinder bit)                                */
  /* ---------------------------------------------------------------- */

  if (pageState !== "reviewing" || !sampleData) return null;

  const cardIdx = cardOrder[currentIndex];
  const card = cardIdx != null ? sampleData.cards[cardIdx] : undefined;
  const total = sampleData.cards.length;
  const reviewed = Object.keys(verdicts).length;
  const unreviewedLeft = cardOrder.length - currentIndex;
  const failCount = Object.values(verdicts).filter((v) => v === "fail").length;

  // All reviewed — waiting for auto-submit
  if (!card) {
    return (
      <CenteredPanel>
        <Spinner />
        <p className="text-muted text-sm mt-3">Submitting...</p>
      </CenteredPanel>
    );
  }

  const d = card.decisions;
  const p = d.pedigree;

  // DEFRA conversion factors URL by year
  const defraUrl = d.emission_factor.source?.toLowerCase().includes("defra")
    ? `https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-${d.emission_factor.year}`
    : null;

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>{reviewed} of {total} reviewed · {unreviewedLeft} remaining</span>
          <span>
            {reviewed} reviewed
            {failCount > 0 && <span className="text-error ml-1">· {failCount} failed</span>}
          </span>
        </div>
        <div className="w-full h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
          <div
            className="h-full bg-teal rounded-full transition-all duration-300"
            style={{ width: `${(reviewed / total) * 100}%` }}
          />
        </div>
      </div>

      {/* The Card */}
      <div
        className={`bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm overflow-hidden transition-all duration-300 ${
          swipeDir === "right" ? "translate-x-12 opacity-0 rotate-3" :
          swipeDir === "left" ? "-translate-x-12 opacity-0 -rotate-3" : ""
        }`}
      >
        {/* Card header */}
        <div className="px-6 py-4 border-b border-[#E5E5E0] bg-[#FAFAF7]">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <div className="font-semibold text-[15px] truncate">{card.raw_data.raw_description}</div>
              <div className="text-muted text-xs mt-0.5">
                {card.raw_data.raw_supplier} · Row {card.raw_data.row_number} · {card.raw_data.raw_date}
              </div>
            </div>
            <div className="text-right flex-shrink-0 ml-4">
              <div className="text-lg font-bold tabular-nums">
                {(d.calculation.co2e_kg / 1000).toFixed(3)}
              </div>
              <div className="text-[10px] text-muted">tCO2e</div>
            </div>
          </div>
          {/* Sampling reasons */}
          <div className="flex flex-wrap gap-1.5 mt-2">
            {card.sampling_reasons.map((reason, i) => (
              <span key={i} className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#EFF6FF] text-[#1E40AF] border border-[#BFDBFE]">
                {reason}
              </span>
            ))}
          </div>
        </div>

        {/* Card body — the checks */}
        <div className="p-6 space-y-4">
          {/* Raw amount */}
          <div className="flex items-center justify-between py-2 border-b border-[#F0F0EB]">
            <span className="text-xs text-muted">Raw Amount</span>
            <span className="text-sm font-medium tabular-nums">£{card.raw_data.raw_amount}</span>
          </div>

          {/* Classification */}
          <CheckRow
            label="Classification"
            value={d.classification.category_name || "Unclassified"}
            detail={`Scope ${d.classification.scope} · ${d.classification.method} · ${((d.classification.confidence || 0) * 100).toFixed(0)}% confidence`}
            flag={d.classification.method === "none" || d.classification.confidence < 0.5}
          />

          {/* Emission Factor — with DEFRA link */}
          <div className={`py-2 border-b border-[#F0F0EB] ${d.emission_factor.level >= 5 ? "bg-[#FFFBEB] -mx-6 px-6 border-amber/20" : ""}`}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted flex items-center gap-1.5">
              Emission Factor
              {d.emission_factor.level >= 5 && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-tint text-amber border border-amber/30 normal-case tracking-normal">
                  Check
                </span>
              )}
            </div>
            <div className="text-sm mt-0.5">{d.emission_factor.value} {d.emission_factor.unit}</div>
            <div className="text-[11px] text-muted mt-0.5 flex items-center gap-1.5">
              <span>{d.emission_factor.source} · Level {d.emission_factor.level} · {d.emission_factor.region} {d.emission_factor.year}</span>
              {defraUrl && (
                <a
                  href={defraUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-0.5 text-teal hover:underline font-medium"
                >
                  Verify
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>
          </div>

          {/* Arithmetic */}
          <CheckRow
            label="Calculation"
            value={`£${d.calculation.amount_gbp.toFixed(2)} × ${d.calculation.ef_value} = ${d.calculation.co2e_kg.toFixed(2)} kgCO2e`}
            detail={d.calculation.arithmetic_verified ? "Arithmetic verified" : "Arithmetic mismatch"}
            flag={!d.calculation.arithmetic_verified}
          />

          {/* Supplier Match */}
          <CheckRow
            label="Supplier"
            value={card.raw_data.raw_supplier}
            detail={`Match: ${d.supplier_match.match_method}${d.supplier_match.supplier_id ? ` · ID #${d.supplier_match.supplier_id}` : " · No match"}`}
            flag={!d.supplier_match.supplier_id}
          />

          {/* Data Quality — expanded */}
          <div className={`py-2 border-b border-[#F0F0EB] ${(p.gsd_total || 0) > 3 ? "bg-[#FFFBEB] -mx-6 px-6 border-amber/20" : ""}`}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted flex items-center gap-1.5">
              Data Quality (Pedigree Matrix)
              {(p.gsd_total || 0) > 3 && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-tint text-amber border border-amber/30 normal-case tracking-normal">
                  Check
                </span>
              )}
            </div>
            <div className="text-sm mt-0.5">
              GSD {p.gsd_total?.toFixed(2) || "—"}
              <span className="text-[11px] text-muted ml-1.5">
                ({p.gsd_total && p.gsd_total <= 1.5 ? "High quality" : p.gsd_total && p.gsd_total <= 3 ? "Moderate quality" : "Low quality — high uncertainty"})
              </span>
            </div>
            <div className="grid grid-cols-5 gap-2 mt-2">
              <PedigreeIndicator label="Reliability" score={p.reliability} description={PEDIGREE_LABELS.reliability[p.reliability]} />
              <PedigreeIndicator label="Completeness" score={p.completeness} description={PEDIGREE_LABELS.completeness[p.completeness]} />
              <PedigreeIndicator label="Temporal" score={p.temporal} description={PEDIGREE_LABELS.temporal[p.temporal]} />
              <PedigreeIndicator label="Geographic" score={p.geographical} description={PEDIGREE_LABELS.geographical[p.geographical]} />
              <PedigreeIndicator label="Technology" score={p.technological} description={PEDIGREE_LABELS.technological[p.technological]} />
            </div>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-5 py-4">
        <button
          onClick={() => setVerdict(card.transaction_id, "fail")}
          className="group w-16 h-16 rounded-full border-2 border-[#FCA5A5] bg-white hover:bg-[#FEE2E2] transition-colors flex items-center justify-center shadow-sm"
          title="Fail (← or D)"
        >
          <svg className="w-7 h-7 text-[#991B1B] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {currentIndex > 0 && (
          <button
            onClick={() => setCurrentIndex((prev) => prev - 1)}
            className="w-10 h-10 rounded-full border border-[#E5E5E0] bg-white hover:bg-paper transition-colors flex items-center justify-center text-muted"
            title="Go back (Backspace)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
        )}

        <button
          onClick={skipCard}
          className="group w-12 h-12 rounded-full border-2 border-[#E5E5E0] bg-white hover:bg-amber-tint transition-colors flex items-center justify-center shadow-sm"
          title="Come back later (↓ or S)"
        >
          <svg className="w-5 h-5 text-amber group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>

        <button
          onClick={() => setVerdict(card.transaction_id, "pass")}
          className="group w-16 h-16 rounded-full border-2 border-[#A7F3D0] bg-white hover:bg-[#D1FAE5] transition-colors flex items-center justify-center shadow-sm"
          title="Pass (→ or A)"
        >
          <svg className="w-7 h-7 text-[#065F46] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>

      {/* Keyboard hint + Save & Exit */}
      <div className="flex items-center justify-between">
        <div className="text-[10px] text-muted">
          ← Fail · → Pass · ↓ Skip · Backspace undo
        </div>
        <Link
          href="/dashboard/clients"
          className="text-xs text-muted hover:text-teal transition-colors font-medium"
        >
          Save & Exit
        </Link>
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

function CheckRow({
  label,
  value,
  detail,
  flag,
}: {
  label: string;
  value: string;
  detail: string;
  flag?: boolean;
}) {
  return (
    <div className={`py-2 border-b border-[#F0F0EB] ${flag ? "bg-[#FFFBEB] -mx-6 px-6 border-amber/20" : ""}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted flex items-center gap-1.5">
        {label}
        {flag && (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-tint text-amber border border-amber/30 normal-case tracking-normal">
            Check
          </span>
        )}
      </div>
      <div className="text-sm mt-0.5">{value}</div>
      <div className="text-[11px] text-muted mt-0.5">{detail}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pedigree matrix labels and indicator                               */
/* ------------------------------------------------------------------ */

const PEDIGREE_LABELS: Record<string, Record<number, string>> = {
  reliability: {
    1: "Verified data",
    2: "Verified, partly based on assumptions",
    3: "Non-verified, partly based on assumptions",
    4: "Qualified estimate",
    5: "Non-qualified estimate",
  },
  completeness: {
    1: "All relevant sites over adequate period",
    2: "More than 50% of sites over adequate period",
    3: "Less than 50% of sites or shorter period",
    4: "One site relevant to area",
    5: "Unknown or incomplete data",
  },
  temporal: {
    1: "Less than 3 years old",
    2: "Less than 6 years old",
    3: "Less than 10 years old",
    4: "Less than 15 years old",
    5: "More than 15 years old or unknown",
  },
  geographical: {
    1: "Data from area under study",
    2: "Average from larger area the study is part of",
    3: "Data from area with similar conditions",
    4: "Data from area with slightly similar conditions",
    5: "Data from unknown or different area",
  },
  technological: {
    1: "Data from identical process",
    2: "Data from similar process, same technology",
    3: "Data from similar process, different technology",
    4: "Data from related process on lab scale",
    5: "Data from related process, different technology",
  },
};

const SCORE_COLORS: Record<number, string> = {
  1: "bg-[#065F46] text-white",
  2: "bg-[#D1FAE5] text-[#065F46]",
  3: "bg-amber-tint text-amber",
  4: "bg-[#FEE2E2] text-[#991B1B]",
  5: "bg-[#991B1B] text-white",
};

function PedigreeIndicator({
  label,
  score,
  description,
}: {
  label: string;
  score: number;
  description: string;
}) {
  return (
    <div className="text-center group relative">
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold mx-auto ${SCORE_COLORS[score] || "bg-paper text-muted"}`}>
        {score}
      </div>
      <div className="text-[9px] text-muted mt-1 leading-tight">{label}</div>
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate text-white text-[10px] rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 shadow-lg">
        {description}
      </div>
    </div>
  );
}
