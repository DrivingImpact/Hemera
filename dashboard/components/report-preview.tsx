"use client";

import { useState } from "react";
import AITaskButtons from "@/components/ai-task-buttons";
import type { Finding } from "@/components/finding-card";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface RecommendedAction {
  id?: number;
  text: string;
  priority?: "high" | "medium" | "low";
}

export interface EngagementTouchpoint {
  id: number;
  date: string;
  type: string;
  notes: string;
}

interface ReportPreviewProps {
  supplierId: number;
  supplierName: string;
  engagementId: string;
  includedFindings: Finding[];
  actions: RecommendedAction[];
  engagements: EngagementTouchpoint[];
  clientLanguage: Record<number, string>; // findingId -> client language
  onActionsGenerated: (text: string) => void;
  onClientLanguage: (findingId: number, text: string) => void;
  onLogEngagement: (type: string, notes: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ReportPreview({
  supplierId,
  supplierName,
  engagementId,
  includedFindings,
  actions,
  engagements,
  clientLanguage,
  onActionsGenerated,
  onClientLanguage,
  onLogEngagement,
}: ReportPreviewProps) {
  const [engType, setEngType] = useState("email");
  const [engNotes, setEngNotes] = useState("");
  const [showEngForm, setShowEngForm] = useState(false);

  return (
    <div className="space-y-6">
      {/* ---- Included Findings ---- */}
      <section>
        <h3 className="text-xs font-bold uppercase tracking-wide text-muted mb-3">
          Included Findings ({includedFindings.length})
        </h3>

        {includedFindings.length === 0 ? (
          <div className="text-sm text-muted bg-[#FAFAF7] rounded-lg px-4 py-6 text-center">
            No findings included yet. Toggle findings on the left panel to
            include them in the report.
          </div>
        ) : (
          <div className="space-y-3">
            {includedFindings.map((f) => (
              <div
                key={f.id}
                className="bg-surface rounded-lg border border-[#E5E5E0] p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-slate">
                      {f.title}
                    </h4>
                    {clientLanguage[f.id] ? (
                      <p className="text-xs text-muted mt-1.5 leading-relaxed whitespace-pre-wrap">
                        {clientLanguage[f.id]}
                      </p>
                    ) : (
                      <p className="text-xs text-muted/60 italic mt-1.5">
                        Client language not yet generated
                      </p>
                    )}
                  </div>
                </div>
                <div className="mt-3">
                  <AITaskButtons
                    taskType="client_language"
                    targetType="finding"
                    targetId={f.id}
                    context={{
                      supplier_name: supplierName,
                      finding_title: f.title,
                      finding_detail: f.detail,
                      finding_severity: f.severity,
                    }}
                    onResult={(text) => onClientLanguage(f.id, text)}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---- Recommended Actions ---- */}
      <section>
        <h3 className="text-xs font-bold uppercase tracking-wide text-muted mb-3">
          Recommended Actions
        </h3>

        {actions.length > 0 ? (
          <div className="space-y-2 mb-3">
            {actions.map((action, i) => (
              <div
                key={action.id ?? i}
                className="flex items-start gap-2 bg-surface rounded-lg border border-[#E5E5E0] p-3"
              >
                {action.priority && (
                  <span
                    className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5 ${
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
                <p className="text-xs text-slate leading-relaxed">
                  {action.text}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted bg-[#FAFAF7] rounded-lg px-4 py-4 text-center mb-3">
            No actions generated yet.
          </div>
        )}

        <AITaskButtons
          taskType="recommended_actions"
          targetType="supplier"
          targetId={supplierId}
          context={{
            supplier_name: supplierName,
            engagement_id: engagementId,
            included_findings: includedFindings.map((f) => ({
              title: f.title,
              severity: f.severity,
              domain: f.domain,
            })),
          }}
          onResult={onActionsGenerated}
        />
      </section>

      {/* ---- Risk Analysis ---- */}
      <section>
        <h3 className="text-xs font-bold uppercase tracking-wide text-muted mb-3">
          Risk Analysis
        </h3>
        <AITaskButtons
          taskType="risk_analysis"
          targetType="supplier"
          targetId={supplierId}
          context={{
            supplier_name: supplierName,
            engagement_id: engagementId,
            findings_count: includedFindings.length,
          }}
          onResult={() => {}}
        />
      </section>

      {/* ---- Hemera Engagement History ---- */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted">
            Engagement History
          </h3>
          <button
            onClick={() => setShowEngForm(!showEngForm)}
            className="text-xs text-teal hover:underline font-medium"
          >
            {showEngForm ? "Cancel" : "+ Log Engagement"}
          </button>
        </div>

        {showEngForm && (
          <div className="bg-[#FAFAF7] rounded-lg border border-[#E5E5E0] p-4 mb-3 space-y-3">
            <div>
              <label className="text-[11px] font-semibold text-muted block mb-1">
                Type
              </label>
              <select
                value={engType}
                onChange={(e) => setEngType(e.target.value)}
                className="w-full text-sm border border-[#E5E5E0] rounded-lg px-3 py-2 bg-white"
              >
                <option value="email">Email</option>
                <option value="call">Call</option>
                <option value="meeting">Meeting</option>
                <option value="site_visit">Site Visit</option>
                <option value="questionnaire">Questionnaire</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-muted block mb-1">
                Notes
              </label>
              <textarea
                value={engNotes}
                onChange={(e) => setEngNotes(e.target.value)}
                className="w-full text-sm border border-[#E5E5E0] rounded-lg px-3 py-2 resize-y min-h-[60px]"
                placeholder="Describe the engagement..."
              />
            </div>
            <button
              onClick={() => {
                onLogEngagement(engType, engNotes);
                setEngNotes("");
                setShowEngForm(false);
              }}
              disabled={!engNotes.trim()}
              className="px-4 py-2 bg-teal text-white text-xs rounded-lg font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              Save Engagement
            </button>
          </div>
        )}

        {engagements.length > 0 ? (
          <div className="space-y-2">
            {engagements.map((eng) => (
              <div
                key={eng.id}
                className="flex items-start gap-3 text-xs bg-surface rounded-lg border border-[#E5E5E0] p-3"
              >
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-[#F1F5F9] text-[#475569] flex-shrink-0 mt-0.5">
                  {eng.type}
                </span>
                <div className="min-w-0">
                  <p className="text-slate leading-relaxed">{eng.notes}</p>
                  <p className="text-muted mt-1">{eng.date}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted bg-[#FAFAF7] rounded-lg px-4 py-4 text-center">
            No engagement touchpoints logged yet.
          </div>
        )}

        {/* Engagement Summary AI */}
        {engagements.length > 0 && (
          <div className="mt-3">
            <AITaskButtons
              taskType="engagement_summary"
              targetType="supplier"
              targetId={supplierId}
              context={{
                supplier_name: supplierName,
                engagements: engagements.map((e) => ({
                  type: e.type,
                  date: e.date,
                  notes: e.notes,
                })),
              }}
              onResult={() => {}}
            />
          </div>
        )}
      </section>
    </div>
  );
}
