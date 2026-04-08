"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SupplierCard {
  card_number: number;
  total_cards: number;
  raw_supplier: string;
  supplier_id: number | null;
  match_method: string;
  matched_name: string | null;
  matched_sector: string | null;
  sic_codes: string[];
  esg_score: number | null;
  ch_number: string | null;
  txn_count: number;
  total_spend: number;
  total_co2e_kg: number;
  sampling_reasons: string[];
}

interface GenerateResponse {
  engagement_id: number;
  population_size: number;
  sample_size: number;
  cards: SupplierCard[];
  summary: {
    total_suppliers: number;
    matched_exact: number;
    matched_fuzzy: number;
    unmatched: number;
  };
}

type PageState = "loading" | "idle" | "generating" | "reviewing" | "done" | "error";

export default function SupplierReviewPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [pageState, setPageState] = useState<PageState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [data, setData] = useState<GenerateResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [cardOrder, setCardOrder] = useState<number[]>([]);
  const [verdicts, setVerdicts] = useState<Record<string, "correct" | "incorrect" | "unsure">>({});
  const [swipeDir, setSwipeDir] = useState<"left" | "right" | null>(null);

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

  // Check engagement status
  useEffect(() => {
    const load = async () => {
      try {
        const eng = await apiFetch<{ status: string }>(`/engagements/${id}`);
        if (eng.status === "delivered" || eng.status === "qc_passed") {
          setPageState("idle");
        } else {
          setErrorMsg("Engagement must be delivered before supplier review");
          setPageState("error");
        }
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load");
        setPageState("error");
      }
    };
    load();
  }, [apiFetch, id]);

  const generate = useCallback(async () => {
    setPageState("generating");
    try {
      const result = await apiFetch<GenerateResponse>(
        `/engagements/${id}/supplier-review/generate`,
        { method: "POST" }
      );
      setData(result);
      setCardOrder(result.cards.map((_: SupplierCard, i: number) => i));
      setCurrentIndex(0);
      setVerdicts({});
      setPageState("reviewing");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to generate");
      setPageState("error");
    }
  }, [apiFetch, id]);

  const setVerdict = useCallback((rawSupplier: string, verdict: "correct" | "incorrect" | "unsure") => {
    setSwipeDir(verdict === "correct" ? "right" : verdict === "incorrect" ? "left" : null);
    setTimeout(() => {
      setVerdicts((prev) => ({ ...prev, [rawSupplier]: verdict }));
      setSwipeDir(null);
      setCurrentIndex((prev) => prev + 1);
    }, 250);
  }, []);

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
    }, 250);
  }, [currentIndex]);

  // Keyboard
  useEffect(() => {
    if (pageState !== "reviewing" || !data) return;
    const cardIdx = cardOrder[currentIndex];
    const card = cardIdx != null ? data.cards[cardIdx] : undefined;
    if (!card) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "a") setVerdict(card.raw_supplier, "correct");
      else if (e.key === "ArrowLeft" || e.key === "d") setVerdict(card.raw_supplier, "incorrect");
      else if (e.key === "ArrowDown" || e.key === "s") skipCard();
      else if (e.key === "Backspace" && currentIndex > 0) setCurrentIndex((p) => p - 1);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pageState, data, cardOrder, currentIndex, setVerdict, skipCard]);

  // Check if done
  useEffect(() => {
    if (pageState === "reviewing" && data && Object.keys(verdicts).length === data.cards.length) {
      setPageState("done");
    }
  }, [pageState, data, verdicts]);

  /* ---- Render ---- */

  if (pageState === "loading" || pageState === "generating") {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
        <p className="text-muted text-sm mt-3">{pageState === "generating" ? "Generating sample..." : "Loading..."}</p>
      </div>
    );
  }

  if (pageState === "error") {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <p className="text-error text-sm">{errorMsg}</p>
        <button onClick={() => setPageState("idle")} className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold">Try Again</button>
      </div>
    );
  }

  if (pageState === "idle") {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-16 h-16 rounded-full bg-[#EDE9FE] flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-[#6366F1]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">Supplier Claims Review</h2>
        <p className="text-muted text-sm mt-1 max-w-sm">
          Verify that supplier matches are correct and risk assessments are justified.
          A statistical sample of supplier claims will be generated for review.
        </p>
        <button
          onClick={generate}
          className="mt-5 px-6 py-3 bg-[#6366F1] text-white rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Generate Supplier Sample
        </button>
      </div>
    );
  }

  if (pageState === "done") {
    const correct = Object.values(verdicts).filter((v) => v === "correct").length;
    const incorrect = Object.values(verdicts).filter((v) => v === "incorrect").length;
    const unsure = Object.values(verdicts).filter((v) => v === "unsure").length;
    const total = Object.keys(verdicts).length;
    const errorRate = total > 0 ? incorrect / total : 0;

    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto ${errorRate <= 0.1 ? "bg-[#D1FAE5]" : "bg-[#FEE2E2]"}`}>
          {errorRate <= 0.1 ? (
            <svg className="w-10 h-10 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-10 h-10 text-[#991B1B]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>
        <h2 className="text-xl font-bold mt-4">Supplier Review Complete</h2>
        <div className="flex items-center gap-6 mt-4">
          <div className="text-center">
            <div className="text-2xl font-bold tabular-nums text-[#065F46]">{correct}</div>
            <div className="text-[11px] text-muted">Correct</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold tabular-nums text-[#991B1B]">{incorrect}</div>
            <div className="text-[11px] text-muted">Incorrect</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold tabular-nums text-amber">{unsure}</div>
            <div className="text-[11px] text-muted">Unsure</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold tabular-nums">{(errorRate * 100).toFixed(1)}%</div>
            <div className="text-[11px] text-muted">Error Rate</div>
          </div>
        </div>
        <div className="flex items-center gap-3 mt-6">
          <Link href="/dashboard/clients" className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90">
            Back to Queue
          </Link>
        </div>
      </div>
    );
  }

  /* ---- Card review ---- */
  if (!data) return null;

  const cardIdx = cardOrder[currentIndex];
  const card = cardIdx != null ? data.cards[cardIdx] : undefined;
  const total = data.cards.length;
  const reviewed = Object.keys(verdicts).length;
  const unreviewedLeft = cardOrder.length - currentIndex;
  const incorrectCount = Object.values(verdicts).filter((v) => v === "incorrect").length;

  if (!card) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">
        <div className="w-10 h-10 rounded-full border-4 border-teal/20 border-t-teal animate-spin" />
        <p className="text-muted text-sm mt-3">Finishing...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>{reviewed} of {total} reviewed · {unreviewedLeft} remaining</span>
          <span>
            {reviewed} reviewed
            {incorrectCount > 0 && <span className="text-error ml-1">· {incorrectCount} incorrect</span>}
          </span>
        </div>
        <div className="w-full h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
          <div className="h-full bg-[#6366F1] rounded-full transition-all duration-300" style={{ width: `${(reviewed / total) * 100}%` }} />
        </div>
      </div>

      {/* Card */}
      <div className={`bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm overflow-hidden transition-all duration-300 ${
        swipeDir === "right" ? "translate-x-12 opacity-0 rotate-3" :
        swipeDir === "left" ? "-translate-x-12 opacity-0 -rotate-3" : ""
      }`}>
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E0] bg-[#FAFAF7]">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold text-[15px]">{card.raw_supplier}</div>
              <div className="text-muted text-xs mt-0.5">
                Raw supplier name from accounting data
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold tabular-nums">£{card.total_spend.toLocaleString()}</div>
              <div className="text-[10px] text-muted">{card.txn_count} transactions</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {card.sampling_reasons.map((r, i) => (
              <span key={i} className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#EDE9FE] text-[#6366F1] border border-[#C4B5FD]">
                {r}
              </span>
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Match result */}
          <div className={`py-3 px-4 rounded-lg ${card.supplier_id ? "bg-[#FAFAF7]" : "bg-[#FFFBEB]"}`}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted mb-1">
              System Match
              <span className={`ml-2 text-[9px] font-bold px-1.5 py-0.5 rounded normal-case tracking-normal ${
                card.match_method === "exact" ? "bg-[#D1FAE5] text-[#065F46]" :
                card.match_method === "fuzzy" ? "bg-amber-tint text-amber" :
                "bg-[#FEE2E2] text-[#991B1B]"
              }`}>
                {card.match_method === "exact" ? "Exact" : card.match_method === "fuzzy" ? "Fuzzy" : "No match"}
              </span>
            </div>
            {card.matched_name ? (
              <div>
                <div className="text-sm font-medium">{card.matched_name}</div>
                <div className="text-[11px] text-muted mt-0.5">
                  {card.matched_sector && <span>{card.matched_sector} · </span>}
                  {card.ch_number && <span>Companies House: {card.ch_number} · </span>}
                  {card.sic_codes && card.sic_codes.length > 0 && <span>SIC: {card.sic_codes.join(", ")}</span>}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted italic">No supplier matched in database</div>
            )}
          </div>

          {/* Impact */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-lg font-bold tabular-nums">{card.txn_count}</div>
              <div className="text-[10px] text-muted">Transactions</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-lg font-bold tabular-nums">{(card.total_co2e_kg / 1000).toFixed(2)}</div>
              <div className="text-[10px] text-muted">tCO2e</div>
            </div>
            <div className="bg-[#FAFAF7] rounded-lg p-3 text-center">
              <div className="text-lg font-bold tabular-nums">{card.esg_score ?? "—"}</div>
              <div className="text-[10px] text-muted">ESG Score</div>
            </div>
          </div>

          {/* Question */}
          <div className="text-center text-sm text-muted pt-2">
            Is <span className="font-semibold text-slate">&quot;{card.raw_supplier}&quot;</span> correctly matched to{" "}
            <span className="font-semibold text-slate">{card.matched_name || "no supplier"}</span>?
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-5 py-4">
        <button
          onClick={() => setVerdict(card.raw_supplier, "incorrect")}
          className="group w-16 h-16 rounded-full border-2 border-[#FCA5A5] bg-white hover:bg-[#FEE2E2] transition-colors flex items-center justify-center shadow-sm"
          title="Incorrect (← or D)"
        >
          <svg className="w-7 h-7 text-[#991B1B] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {currentIndex > 0 && (
          <button
            onClick={() => setCurrentIndex((p) => p - 1)}
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
          onClick={() => setVerdict(card.raw_supplier, "correct")}
          className="group w-16 h-16 rounded-full border-2 border-[#A7F3D0] bg-white hover:bg-[#D1FAE5] transition-colors flex items-center justify-center shadow-sm"
          title="Correct (→ or A)"
        >
          <svg className="w-7 h-7 text-[#065F46] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-[10px] text-muted">
          ← Incorrect · → Correct · ↓ Skip · Backspace undo
        </div>
        <Link href="/dashboard/clients" className="text-xs text-muted hover:text-teal transition-colors font-medium">
          Save & Exit
        </Link>
      </div>
    </div>
  );
}
