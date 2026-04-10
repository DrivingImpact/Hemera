"use client";

/* ------------------------------------------------------------------ */
/*  FindingCard — individual finding with include/skip toggle          */
/* ------------------------------------------------------------------ */

export interface EvidenceItem {
  source_name: string;
  tier?: number;
  summary?: string;
  data?: Record<string, unknown>;
  fetched_at?: string;
  is_verified?: boolean;
}

export interface Finding {
  id: number;
  source: "deterministic" | "ai" | "ai_automated" | "ai_manual" | "outlier";
  domain: string;
  severity: "critical" | "high" | "medium" | "info" | "positive";
  title: string;
  detail: string;
  evidence_url?: string | null;
  source_name?: string;
  layer?: number | null;
  evidence?: EvidenceItem[];
  included: boolean | null; // null = not yet decided
}

interface FindingCardProps {
  finding: Finding;
  onToggle: (findingId: number, included: boolean) => void;
}

const SEVERITY_STYLES: Record<
  Finding["severity"],
  { border: string; badge: string; badgeBg: string }
> = {
  critical: {
    border: "border-l-[#DC2626]",
    badge: "text-[#991B1B]",
    badgeBg: "bg-[#FEE2E2]",
  },
  high: {
    border: "border-l-[#F59E0B]",
    badge: "text-[#92400E]",
    badgeBg: "bg-[#FEF3C7]",
  },
  medium: {
    border: "border-l-[#EAB308]",
    badge: "text-[#854D0E]",
    badgeBg: "bg-[#FEF9C3]",
  },
  info: {
    border: "border-l-[#3B82F6]",
    badge: "text-[#1E40AF]",
    badgeBg: "bg-[#EFF6FF]",
  },
  positive: {
    border: "border-l-[#059669]",
    badge: "text-[#065F46]",
    badgeBg: "bg-[#D1FAE5]",
  },
};

const SOURCE_LABELS: Record<string, string> = {
  deterministic: "Deterministic",
  ai: "AI Analysis",
  ai_automated: "AI Analysis",
  ai_manual: "AI Analysis (Manual)",
  outlier: "Outlier Detection",
};

export default function FindingCard({ finding, onToggle }: FindingCardProps) {
  const style = SEVERITY_STYLES[finding.severity];
  const isIncluded = finding.included === true;
  const isSkipped = finding.included === false;

  return (
    <div
      className={`border-l-4 ${style.border} bg-surface rounded-lg border border-[#E5E5E0] shadow-sm transition-all duration-200 ${
        isSkipped ? "opacity-50" : ""
      }`}
    >
      <div className="p-4">
        {/* Header: severity + domain + source */}
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${style.badge} ${style.badgeBg}`}
          >
            {finding.severity}
          </span>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#F1F5F9] text-[#475569]">
            {finding.domain}
          </span>
          <span className="text-[10px] text-muted ml-auto">
            {SOURCE_LABELS[finding.source]}
            {finding.source_name ? ` — ${finding.source_name}` : ""}
          </span>
        </div>

        {/* Title + detail */}
        <h4 className="text-sm font-semibold mt-2 text-slate">
          {finding.title}
        </h4>
        <p className="text-xs text-muted mt-1 leading-relaxed">
          {finding.detail}
        </p>

        {/* Evidence breakdown — shows what data sources contributed */}
        {finding.evidence && finding.evidence.length > 0 && (
          <div className="mt-2 space-y-1">
            {finding.evidence.map((ev, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px] bg-[#F8FAFC] rounded px-2.5 py-1.5 border border-[#F0F0EB]">
                <span className={`flex-shrink-0 mt-0.5 w-3.5 h-3.5 rounded-full flex items-center justify-center text-[8px] font-bold ${ev.is_verified ? "bg-teal/15 text-teal" : "bg-[#E5E5E0] text-muted"}`}>
                  {ev.is_verified ? "✓" : "?"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-[#334155]">{ev.source_name}</span>
                    {ev.tier && (
                      <span className="text-[9px] text-muted px-1 py-0 rounded bg-[#F1F5F9]">Tier {ev.tier}</span>
                    )}
                    {finding.layer && (
                      <span className="text-[9px] text-muted px-1 py-0 rounded bg-[#F1F5F9]">L{finding.layer}</span>
                    )}
                    {ev.fetched_at && (
                      <span className="text-[9px] text-muted ml-auto">{new Date(ev.fetched_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span>
                    )}
                  </div>
                  {ev.summary && (
                    <p className="text-muted mt-0.5 leading-snug">{ev.summary}</p>
                  )}
                  {ev.data && Object.keys(ev.data).length > 0 && (
                    <details className="mt-1">
                      <summary className="text-[10px] text-teal cursor-pointer hover:underline">Raw data</summary>
                      <pre className="text-[9px] text-muted mt-1 overflow-x-auto max-h-32 bg-white rounded p-1.5 border border-[#E5E5E0]">
                        {JSON.stringify(ev.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Evidence link */}
        {finding.evidence_url && (
          <a
            href={finding.evidence_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] text-teal hover:underline font-medium mt-2"
          >
            View evidence
            <svg
              className="w-3 h-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        )}

        {/* Include / Skip toggle */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[#F0F0EB]">
          <button
            onClick={() => onToggle(finding.id, true)}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
              isIncluded
                ? "bg-teal text-white"
                : "border border-[#E5E5E0] text-muted hover:bg-[#F0F0EB]"
            }`}
          >
            Include
          </button>
          <button
            onClick={() => onToggle(finding.id, false)}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
              isSkipped
                ? "bg-[#64748B] text-white"
                : "border border-[#E5E5E0] text-muted hover:bg-[#F0F0EB]"
            }`}
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  );
}
