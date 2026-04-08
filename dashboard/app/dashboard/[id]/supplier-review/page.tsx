"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Claim {
  category: string;
  claim: string;
  source: string;
  verifiable: boolean;
  flag?: boolean;
}

interface SupplierCard {
  card_number: number;
  total_cards: number;
  supplier_id: number;
  name: string;
  legal_name: string | null;
  ch_number: string | null;
  sector: string | null;
  entity_type: string | null;
  status: string | null;
  sic_codes: string[];
  esg_score: number | null;
  confidence: string | null;
  critical_flag: boolean;
  raw_supplier: string;
  match_method: string;
  txn_count: number;
  total_spend: number;
  total_co2e_kg: number;
  claims: Claim[];
  sampling_reasons: string[];
}

interface GenerateResponse {
  engagement_id: number;
  population_size: number;
  sample_size: number;
  cards: SupplierCard[];
  summary: {
    total_suppliers: number;
    critical_flagged: number;
    low_confidence: number;
    fuzzy_matched: number;
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
  const [verdicts, setVerdicts] = useState<Record<number, "verified" | "disputed">>({});
  const [swipeDir, setSwipeDir] = useState<"left" | "right" | null>(null);

  const apiFetch = useCallback(
    async <T,>(path: string, options?: RequestInit): Promise<T> => {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...options?.headers },
      });
      if (!res.ok) { const text = await res.text(); throw new Error(text || `API error ${res.status}`); }
      return res.json();
    },
    [getToken]
  );

  useEffect(() => {
    const load = async () => {
      try {
        const eng = await apiFetch<{ status: string }>(`/engagements/${id}`);
        if (eng.status === "delivered" || eng.status === "qc_passed") setPageState("idle");
        else { setErrorMsg("Engagement must be delivered before supplier review"); setPageState("error"); }
      } catch (err) { setErrorMsg(err instanceof Error ? err.message : "Failed to load"); setPageState("error"); }
    };
    load();
  }, [apiFetch, id]);

  const generate = useCallback(async () => {
    setPageState("generating");
    try {
      const result = await apiFetch<GenerateResponse>(`/engagements/${id}/supplier-review/generate`, { method: "POST" });
      setData(result);
      setCardOrder(result.cards.map((_: SupplierCard, i: number) => i));
      setCurrentIndex(0);
      setVerdicts({});
      setPageState("reviewing");
    } catch (err) { setErrorMsg(err instanceof Error ? err.message : "Failed to generate"); setPageState("error"); }
  }, [apiFetch, id]);

  const setVerdict = useCallback((supplierId: number, verdict: "verified" | "disputed") => {
    setSwipeDir(verdict === "verified" ? "right" : "left");
    setTimeout(() => {
      setVerdicts((prev) => ({ ...prev, [supplierId]: verdict }));
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

  useEffect(() => {
    if (pageState !== "reviewing" || !data) return;
    const cardIdx = cardOrder[currentIndex];
    const card = cardIdx != null ? data.cards[cardIdx] : undefined;
    if (!card) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "a") setVerdict(card.supplier_id, "verified");
      else if (e.key === "ArrowLeft" || e.key === "d") setVerdict(card.supplier_id, "disputed");
      else if (e.key === "ArrowDown" || e.key === "s") skipCard();
      else if (e.key === "Backspace" && currentIndex > 0) setCurrentIndex((p) => p - 1);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pageState, data, cardOrder, currentIndex, setVerdict, skipCard]);

  useEffect(() => {
    if (pageState === "reviewing" && data && Object.keys(verdicts).length === data.cards.length) setPageState("done");
  }, [pageState, data, verdicts]);

  /* ---- Loading / Error / Idle ---- */

  if (pageState === "loading" || pageState === "generating") {
    return <Center><Spinner /><p className="text-muted text-sm mt-3">{pageState === "generating" ? "Generating sample..." : "Loading..."}</p></Center>;
  }
  if (pageState === "error") {
    return <Center><p className="text-error text-sm">{errorMsg}</p><button onClick={() => setPageState("idle")} className="mt-4 px-5 py-2.5 bg-slate text-white rounded-lg text-sm font-semibold">Try Again</button></Center>;
  }
  if (pageState === "idle") {
    return (
      <Center>
        <div className="w-16 h-16 rounded-full bg-[#EDE9FE] flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-[#6366F1]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold mt-4">Supplier Claims Review</h2>
        <p className="text-muted text-sm mt-1 max-w-sm">
          Verify the claims we make about each supplier in the report — ESG scores,
          risk flags, sector classifications, and evidence from data sources.
        </p>
        <button onClick={generate} className="mt-5 px-6 py-3 bg-[#6366F1] text-white rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity">
          Generate Claims Sample
        </button>
      </Center>
    );
  }

  /* ---- Done ---- */

  if (pageState === "done") {
    const verified = Object.values(verdicts).filter((v) => v === "verified").length;
    const disputed = Object.values(verdicts).filter((v) => v === "disputed").length;
    const total = Object.keys(verdicts).length;
    const disputeRate = total > 0 ? disputed / total : 0;
    return (
      <Center>
        <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto ${disputeRate <= 0.1 ? "bg-[#D1FAE5]" : "bg-[#FEE2E2]"}`}>
          {disputeRate <= 0.1 ? (
            <svg className="w-10 h-10 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
          ) : (
            <svg className="w-10 h-10 text-[#991B1B]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          )}
        </div>
        <h2 className="text-xl font-bold mt-4">Claims Review Complete</h2>
        <div className="flex items-center gap-6 mt-4">
          <Stat value={verified} label="Verified" color="text-[#065F46]" />
          <Stat value={disputed} label="Disputed" color="text-[#991B1B]" />
          <Stat value={`${(disputeRate * 100).toFixed(1)}%`} label="Dispute Rate" />
        </div>
        {disputed > 0 && (
          <p className="text-muted text-xs mt-3 max-w-sm">
            {disputed} supplier{disputed !== 1 ? "s have" : " has"} disputed claims that should be corrected before the report is released.
          </p>
        )}
        <div className="flex items-center gap-3 mt-6">
          <Link href="/dashboard/clients" className="px-5 py-2.5 bg-[#6366F1] text-white rounded-lg text-sm font-semibold hover:opacity-90">Back to Queue</Link>
        </div>
      </Center>
    );
  }

  /* ---- Card Review ---- */

  if (!data) return null;
  const cardIdx = cardOrder[currentIndex];
  const card = cardIdx != null ? data.cards[cardIdx] : undefined;
  const total = data.cards.length;
  const reviewed = Object.keys(verdicts).length;
  const disputed = Object.values(verdicts).filter((v) => v === "disputed").length;

  if (!card) return <Center><Spinner /><p className="text-muted text-sm mt-3">Finishing...</p></Center>;

  const flaggedClaims = card.claims.filter((c) => c.flag);
  const otherClaims = card.claims.filter((c) => !c.flag);

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>{reviewed} of {total} reviewed · {cardOrder.length - currentIndex} remaining</span>
          {disputed > 0 && <span className="text-error">{disputed} disputed</span>}
        </div>
        <div className="w-full h-1.5 bg-[#E5E5E0] rounded-full overflow-hidden">
          <div className="h-full bg-[#6366F1] rounded-full transition-all duration-300" style={{ width: `${(reviewed / total) * 100}%` }} />
        </div>
      </div>

      {/* Card */}
      <div className={`bg-surface rounded-2xl border border-[#E5E5E0] shadow-sm overflow-hidden transition-all duration-300 ${
        swipeDir === "right" ? "translate-x-12 opacity-0 rotate-3" : swipeDir === "left" ? "-translate-x-12 opacity-0 -rotate-3" : ""
      }`}>
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E0] bg-[#FAFAF7]">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-[15px]">{card.name}</span>
                {card.critical_flag && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5]">Critical</span>
                )}
              </div>
              <div className="text-muted text-xs mt-0.5">
                {card.legal_name && card.legal_name !== card.name && <span>{card.legal_name} · </span>}
                {card.ch_number && <span>CH {card.ch_number} · </span>}
                {card.entity_type && <span>{card.entity_type} · </span>}
                {card.sector}
              </div>
              {card.raw_supplier !== card.name && (
                <div className="text-[10px] text-muted mt-1">
                  Matched from: &quot;{card.raw_supplier}&quot;
                  <span className={`ml-1 font-semibold ${card.match_method === "exact" ? "text-[#065F46]" : "text-amber"}`}>
                    ({card.match_method})
                  </span>
                </div>
              )}
            </div>
            <div className="text-right flex-shrink-0 ml-4">
              <div className="text-lg font-bold tabular-nums">£{card.total_spend.toLocaleString()}</div>
              <div className="text-[10px] text-muted">{card.txn_count} txns · {(card.total_co2e_kg / 1000).toFixed(2)} tCO2e</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {card.sampling_reasons.map((r, i) => (
              <span key={i} className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#EDE9FE] text-[#6366F1] border border-[#C4B5FD]">{r}</span>
            ))}
          </div>
        </div>

        {/* Claims to verify */}
        <div className="p-6 space-y-3">
          <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
            Claims in report ({card.claims.length})
          </div>

          {/* Flagged claims first */}
          {flaggedClaims.length > 0 && (
            <div className="space-y-2">
              {flaggedClaims.map((claim, i) => (
                <ClaimRow key={`flag-${i}`} claim={claim} />
              ))}
            </div>
          )}

          {/* Other claims */}
          {otherClaims.length > 0 && (
            <div className="space-y-2">
              {otherClaims.map((claim, i) => (
                <ClaimRow key={`claim-${i}`} claim={claim} />
              ))}
            </div>
          )}

          {/* ESG score summary if available */}
          {card.esg_score != null && (
            <div className="flex items-center gap-3 pt-2 border-t border-[#F0F0EB]">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                card.esg_score >= 70 ? "bg-[#D1FAE5] text-[#065F46]" :
                card.esg_score >= 40 ? "bg-amber-tint text-amber" :
                "bg-[#FEE2E2] text-[#991B1B]"
              }`}>
                {card.esg_score.toFixed(0)}
              </div>
              <div>
                <div className="text-xs font-medium">ESG Score</div>
                <div className="text-[10px] text-muted">
                  {card.confidence} confidence
                  {card.esg_score >= 70 ? " · Low risk" : card.esg_score >= 40 ? " · Medium risk" : " · High risk"}
                </div>
              </div>
            </div>
          )}

          {/* Question */}
          <div className="text-center text-sm text-muted pt-3 border-t border-[#F0F0EB]">
            Are these claims about <span className="font-semibold text-slate">{card.name}</span> accurate?
          </div>
        </div>
      </div>

      {/* Buttons */}
      <div className="flex items-center justify-center gap-5 py-4">
        <button onClick={() => setVerdict(card.supplier_id, "disputed")} className="group w-16 h-16 rounded-full border-2 border-[#FCA5A5] bg-white hover:bg-[#FEE2E2] transition-colors flex items-center justify-center shadow-sm" title="Dispute (← or D)">
          <svg className="w-7 h-7 text-[#991B1B] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
        {currentIndex > 0 && (
          <button onClick={() => setCurrentIndex((p) => p - 1)} className="w-10 h-10 rounded-full border border-[#E5E5E0] bg-white hover:bg-paper transition-colors flex items-center justify-center text-muted" title="Go back">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          </button>
        )}
        <button onClick={skipCard} className="group w-12 h-12 rounded-full border-2 border-[#E5E5E0] bg-white hover:bg-amber-tint transition-colors flex items-center justify-center shadow-sm" title="Skip (↓ or S)">
          <svg className="w-5 h-5 text-amber group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        </button>
        <button onClick={() => setVerdict(card.supplier_id, "verified")} className="group w-16 h-16 rounded-full border-2 border-[#A7F3D0] bg-white hover:bg-[#D1FAE5] transition-colors flex items-center justify-center shadow-sm" title="Verify (→ or A)">
          <svg className="w-7 h-7 text-[#065F46] group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-[10px] text-muted">← Dispute · → Verify · ↓ Skip · Backspace undo</div>
        <Link href="/dashboard/clients" className="text-xs text-muted hover:text-teal transition-colors font-medium">Save & Exit</Link>
      </div>
    </div>
  );
}

/* ---- Shared ---- */

function Center({ children }: { children: React.ReactNode }) {
  return <div className="max-w-md mx-auto flex flex-col items-center text-center py-16">{children}</div>;
}
function Spinner() {
  return <div className="w-10 h-10 rounded-full border-4 border-[#6366F1]/20 border-t-[#6366F1] animate-spin" />;
}
function Stat({ value, label, color }: { value: number | string; label: string; color?: string }) {
  return (
    <div className="text-center">
      <div className={`text-2xl font-bold tabular-nums ${color || ""}`}>{value}</div>
      <div className="text-[11px] text-muted">{label}</div>
    </div>
  );
}

function ClaimRow({ claim }: { claim: Claim }) {
  return (
    <div className={`rounded-lg px-4 py-2.5 ${claim.flag ? "bg-[#FFFBEB] border border-amber/20" : "bg-[#FAFAF7]"}`}>
      <div className="flex items-start gap-2">
        {claim.flag && (
          <span className="flex-shrink-0 mt-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-tint text-amber border border-amber/30">
            Flag
          </span>
        )}
        <div className="min-w-0">
          <div className="text-xs">{claim.claim}</div>
          <div className="text-[10px] text-muted mt-0.5">
            <span className="font-medium">{claim.category}</span> · {claim.source}
          </div>
        </div>
      </div>
    </div>
  );
}
