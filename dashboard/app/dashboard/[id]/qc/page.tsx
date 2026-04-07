"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
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
  const router = useRouter();
  const { getToken } = useAuth();

  const [pageState, setPageState] = useState<PageState>("loading_status");
  const [errorMsg, setErrorMsg] = useState("");
  const [sampleData, setSampleData] = useState<GenerateResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [verdicts, setVerdicts] = useState<Record<number, "pass" | "fail">>({});
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
        const data = await apiFetch<{ status: string }>(`/engagements/${id}`);
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

  /* --- Generate sample --- */
  const generateSample = useCallback(async () => {
    setPageState("loading");
    try {
      const data = await apiFetch<GenerateResponse>(
        `/engagements/${id}/qc/generate`,
        { method: "POST" }
      );
      setSampleData(data);
      setCurrentIndex(0);
      setVerdicts({});
      setPageState("reviewing");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to generate sample");
      setPageState("error");
    }
  }, [apiFetch, id]);

  /* --- Verdict handler --- */
  const setVerdict = useCallback((txnId: number, verdict: "pass" | "fail") => {
    setSwipeDir(verdict === "pass" ? "right" : "left");
    setTimeout(() => {
      setVerdicts((prev) => ({ ...prev, [txnId]: verdict }));
      setSwipeDir(null);
      setCurrentIndex((prev) => prev + 1);
    }, 300);
  }, []);

  /* --- Keyboard shortcuts --- */
  useEffect(() => {
    if (pageState !== "reviewing" || !sampleData) return;
    const card = sampleData.cards[currentIndex];
    if (!card) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "a") {
        setVerdict(card.transaction_id, "pass");
      } else if (e.key === "ArrowLeft" || e.key === "d") {
        setVerdict(card.transaction_id, "fail");
      } else if (e.key === "Backspace" && currentIndex > 0) {
        setCurrentIndex((prev) => prev - 1);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pageState, sampleData, currentIndex, setVerdict]);

  /* --- Submit all verdicts --- */
  const submitAll = useCallback(async () => {
    if (!sampleData) return;
    setPageState("submitting");
    try {
      const results = sampleData.cards.map((c) => ({
        transaction_id: c.transaction_id,
        classification_pass: verdicts[c.transaction_id] === "pass",
        emission_factor_pass: verdicts[c.transaction_id] === "pass",
        arithmetic_pass: verdicts[c.transaction_id] === "pass",
        supplier_match_pass: verdicts[c.transaction_id] === "pass",
        pedigree_pass: verdicts[c.transaction_id] === "pass",
        notes: verdicts[c.transaction_id] === "fail" ? "Failed QC review" : "",
      }));
      const data = await apiFetch<SubmitResponse>(`/engagements/${id}/qc/submit`, {
        method: "POST",
        body: JSON.stringify({ results }),
      });
      setSubmitResponse(data);
      setPageState("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Submission failed");
      setPageState("error");
    }
  }, [apiFetch, id, sampleData, verdicts]);

  /* --- Auto-submit when all cards reviewed --- */
  useEffect(() => {
    if (
      pageState === "reviewing" &&
      sampleData &&
      currentIndex >= sampleData.cards.length &&
      Object.keys(verdicts).length === sampleData.cards.length
    ) {
      submitAll();
    }
  }, [pageState, sampleData, currentIndex, verdicts, submitAll]);

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
          Processing classifies transactions and calculates the carbon footprint.
        </p>
        <button
          onClick={triggerProcessing}
          disabled={pageState === "triggering"}
          className="mt-5 px-6 py-3 bg-slate text-white rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {pageState === "triggering" ? "Starting..." : "Start Processing"}
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

  const card = sampleData.cards[currentIndex];
  const total = sampleData.cards.length;
  const reviewed = Object.keys(verdicts).length;
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

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>Card {currentIndex + 1} of {total}</span>
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

          {/* Emission Factor */}
          <CheckRow
            label="Emission Factor"
            value={`${d.emission_factor.value} ${d.emission_factor.unit}`}
            detail={`${d.emission_factor.source} · Level ${d.emission_factor.level} · ${d.emission_factor.region} ${d.emission_factor.year}`}
            flag={d.emission_factor.level >= 5}
          />

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

          {/* Data Quality */}
          <CheckRow
            label="Data Quality"
            value={`GSD ${d.pedigree.gsd_total?.toFixed(2) || "—"}`}
            detail={`R${d.pedigree.reliability} C${d.pedigree.completeness} T${d.pedigree.temporal} G${d.pedigree.geographical} Te${d.pedigree.technological}`}
            flag={(d.pedigree.gsd_total || 0) > 3}
          />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-6 py-4">
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
          onClick={() => setVerdict(card.transaction_id, "pass")}
          className="group w-16 h-16 rounded-full border-2 border-[#A7F3D0] bg-white hover:bg-[#D1FAE5] transition-colors flex items-center justify-center shadow-sm"
          title="Pass (→ or A)"
        >
          <svg className="w-7 h-7 text-[#065F46] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>

      {/* Keyboard hint */}
      <div className="text-center text-[10px] text-muted">
        ← Fail · → Pass · Backspace to go back
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
    <div className={`flex items-start justify-between py-2 border-b border-[#F0F0EB] ${flag ? "bg-[#FFFBEB] -mx-6 px-6 border-amber/20" : ""}`}>
      <div className="min-w-0">
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
    </div>
  );
}
