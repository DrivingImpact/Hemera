import { getReduction, getEngagement } from "@/lib/api";
import { KpiCard } from "@/components/ui/kpi-card";
import { ChartCard } from "@/components/ui/chart-card";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { PendingBanner } from "@/components/ui/pending-banner";
import { ReductionWaterfall } from "@/components/charts/waterfall";
import { ImpactEffortQuadrant } from "@/components/charts/quadrant";
import { fmtTonnes, fmtPct } from "@/lib/format";
import type { ReductionRec } from "@/lib/types";

export default async function ReductionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engagementId = Number(id);

  let engagement;
  try {
    engagement = await getEngagement(engagementId);
  } catch {
    return (
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold">Reduction Roadmap</h1>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm">No data yet.</p>
        </div>
      </div>
    );
  }

  if (engagement.status !== "qc_passed") {
    return (
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold">Reduction Roadmap</h1>
          <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
        </div>
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-2 gap-4">
          <ChartCard title="Year 3 Target">
            <div className="flex items-center justify-center h-24">
              <div className="w-16 h-16 rounded-lg bg-[#E5E5E0] opacity-40" />
            </div>
          </ChartCard>
          <ChartCard title="Total Reduction Potential">
            <div className="flex items-center justify-center h-24">
              <div className="w-16 h-16 rounded-lg bg-[#E5E5E0] opacity-40" />
            </div>
          </ChartCard>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <ChartCard title="Impact vs Effort">
            <div className="flex items-end justify-around h-40 px-4 pb-2">
              {[30, 55, 70, 45, 80, 60, 35].map((h, i) => (
                <div key={i} className="w-6 rounded-t bg-[#E5E5E0] opacity-40" style={{ height: `${h}%` }} />
              ))}
            </div>
          </ChartCard>
          <ChartCard title="Reduction Waterfall">
            <div className="flex items-end justify-around h-40 px-4 pb-2">
              {[100, 85, 72, 62, 54, 48, 43].map((h, i) => (
                <div key={i} className="w-6 rounded-t bg-[#E5E5E0] opacity-40" style={{ height: `${h}%` }} />
              ))}
            </div>
          </ChartCard>
        </div>
        <div className="bg-surface rounded-lg border border-[#E5E5E0]">
          <div className="px-5 py-4 border-b border-[#E5E5E0]">
            <h4 className="text-xs font-semibold uppercase tracking-[0.5px]">All Recommendations</h4>
          </div>
          <div className="p-4 space-y-2">
            {[80, 65, 55, 45, 35].map((w, i) => (
              <div key={i} className="h-3 rounded bg-[#E5E5E0] opacity-30" style={{ width: `${w}%` }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const [data] = await Promise.all([
    getReduction(engagementId),
  ]);

  const { recommendations, projections } = data;

  // Build waterfall reductions from top recommendations
  const waterfallReductions = recommendations
    .slice(0, 8)
    .map((r) => ({
      action: r.action.length > 22 ? r.action.slice(0, 20) + "…" : r.action,
      reduction_tonnes: r.potential_reduction_kg / 1000,
    }));

  const effortVariant = (effort: string) => {
    const e = effort.toLowerCase();
    if (e === "low") return "green" as const;
    if (e === "medium") return "amber" as const;
    return "red" as const;
  };

  const typeVariant = (type: string) => {
    const t = type.toLowerCase();
    if (t === "switch") return "teal" as const;
    if (t === "reduce") return "amber" as const;
    return "slate" as const;
  };

  const columns = [
    { key: "action", label: "Action" },
    {
      key: "type",
      label: "Type",
      render: (row: ReductionRec) => (
        <Badge variant={typeVariant(row.type)}>{row.type}</Badge>
      ),
    },
    {
      key: "current_co2e_kg",
      label: "Current tCO₂e",
      align: "right" as const,
      render: (row: ReductionRec) => fmtTonnes(row.current_co2e_kg / 1000),
    },
    {
      key: "potential_reduction_kg",
      label: "Reduction",
      align: "right" as const,
      render: (row: ReductionRec) =>
        `${fmtTonnes(row.potential_reduction_kg / 1000)}t (${fmtPct(row.potential_reduction_pct)})`,
    },
    {
      key: "effort",
      label: "Effort",
      render: (row: ReductionRec) => (
        <Badge variant={effortVariant(row.effort)}>{row.effort}</Badge>
      ),
    },
    { key: "timeline", label: "Timeline" },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Reduction Roadmap</h1>
        <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <KpiCard
          label="Year 3 Target"
          value={fmtTonnes(projections.year3_target)}
          unit="tCO₂e"
          color="teal"
        />
        <KpiCard
          label="Total Reduction Potential"
          value={fmtTonnes(projections.total_reduction)}
          unit="tCO₂e"
          color="slate"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <ChartCard title="Impact vs Effort">
          <ImpactEffortQuadrant
            recommendations={recommendations.map((r) => ({
              action: r.action,
              effort: r.effort,
              potential_reduction_kg: r.potential_reduction_kg,
              type: r.type,
            }))}
          />
        </ChartCard>

        <ChartCard title="Reduction Waterfall">
          <ReductionWaterfall
            baseline={projections.baseline}
            reductions={waterfallReductions}
          />
        </ChartCard>
      </div>

      <div className="bg-surface rounded-lg border border-[#E5E5E0]">
        <div className="px-5 py-4 border-b border-[#E5E5E0]">
          <h4 className="text-xs font-semibold uppercase tracking-[0.5px]">
            All Recommendations ({recommendations.length})
          </h4>
        </div>
        <div className="overflow-x-auto">
          <DataTable<ReductionRec & Record<string, unknown>>
            columns={columns}
            rows={recommendations as (ReductionRec & Record<string, unknown>)[]}
          />
        </div>
      </div>
    </div>
  );
}
