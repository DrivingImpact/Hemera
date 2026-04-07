import { getReduction, getEngagement } from "@/lib/api";
import { KpiCard } from "@/components/ui/kpi-card";
import { ChartCard } from "@/components/ui/chart-card";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
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

  const [data, engagement] = await Promise.all([
    getReduction(engagementId),
    getEngagement(engagementId),
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
