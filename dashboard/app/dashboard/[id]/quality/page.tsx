import { getDataQuality, getEngagement } from "@/lib/api";
import { KpiCard } from "@/components/ui/kpi-card";
import { ChartCard } from "@/components/ui/chart-card";
import { Badge } from "@/components/ui/badge";
import { PendingBanner } from "@/components/ui/pending-banner";
import { PlotlyChart } from "@/components/charts/plotly-wrapper";

export default async function DataQualityPage({
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
          <h1 className="text-2xl font-bold">Data Quality</h1>
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
          <h1 className="text-2xl font-bold">Data Quality</h1>
          <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
        </div>
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-2 gap-4">
          <ChartCard title="Data Quality Grade">
            <div className="flex items-center justify-center h-24">
              <div className="w-16 h-16 rounded-lg bg-[#E5E5E0] opacity-40" />
            </div>
          </ChartCard>
          <ChartCard title="Average GSD">
            <div className="flex items-center justify-center h-24">
              <div className="w-16 h-16 rounded-lg bg-[#E5E5E0] opacity-40" />
            </div>
          </ChartCard>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <ChartCard title="Pedigree Matrix Scores">
            <div className="flex items-center justify-center h-40">
              <div className="w-32 h-32 rounded-full border-4 border-[#E5E5E0] opacity-40" />
            </div>
          </ChartCard>
          <ChartCard title="Cascade Distribution (Current vs Target)">
            <div className="flex items-end justify-around h-40 px-4 pb-2">
              {[50, 70, 40, 65, 55].map((h, i) => (
                <div key={i} className="w-8 rounded-t bg-[#E5E5E0] opacity-40" style={{ height: `${h}%` }} />
              ))}
            </div>
          </ChartCard>
        </div>
      </div>
    );
  }

  const report = await getDataQuality(engagementId);

  // Pull nested data out safely
  const summary = (report.summary ?? {}) as Record<string, unknown>;
  const cascadeDistribution = (report.cascade_distribution ?? {}) as Record<
    string,
    { current_pct: number; target_pct: number }
  >;
  const pedigreeBreakdown = (report.pedigree_breakdown ?? {}) as Record<string, number>;
  const recommendations = (report.recommendations ?? []) as Array<{
    action: string;
    impact: string;
    description?: string;
  }>;

  const grade = (summary.grade as string) ?? "N/A";
  const avgGsd = typeof summary.avg_gsd === "number" ? summary.avg_gsd.toFixed(2) : "N/A";

  // Pedigree radar
  const pedigreeLabels = Object.keys(pedigreeBreakdown);
  const pedigreeValues = Object.values(pedigreeBreakdown);
  const closedPedigreeLabels = pedigreeLabels.length > 0 ? [...pedigreeLabels, pedigreeLabels[0]] : [];
  const closedPedigreeValues = pedigreeValues.length > 0 ? [...pedigreeValues, pedigreeValues[0]] : [];

  // Cascade bar chart
  const cascadeLevels = Object.keys(cascadeDistribution).sort();
  const currentPcts = cascadeLevels.map((l) => cascadeDistribution[l]?.current_pct ?? 0);
  const targetPcts = cascadeLevels.map((l) => cascadeDistribution[l]?.target_pct ?? 0);

  const gradeColor =
    grade === "A"
      ? "success"
      : grade === "B"
      ? "teal"
      : grade === "C"
      ? "amber"
      : "error";

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Data Quality</h1>
        <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4">
        <KpiCard
          label="Data Quality Grade"
          value={grade}
          color={gradeColor as "teal" | "slate" | "amber" | "success" | "error"}
        />
        <KpiCard label="Average GSD" value={avgGsd} color="teal" />
      </div>

      {/* 2-col: Pedigree radar + Cascade bar */}
      <div className="grid grid-cols-2 gap-4">
        {pedigreeLabels.length > 0 && (
          <ChartCard title="Pedigree Matrix Scores">
            <PlotlyChart
              data={[
                {
                  type: "scatterpolar",
                  fill: "toself",
                  r: closedPedigreeValues,
                  theta: closedPedigreeLabels,
                  line: { color: "#0D9488", width: 2 },
                  fillcolor: "#0D948833",
                  hovertemplate: "<b>%{theta}</b><br>Score: %{r:.2f}<extra></extra>",
                },
              ]}
              layout={{
                polar: {
                  radialaxis: {
                    range: [0, 5],
                    tickfont: { size: 10 },
                  },
                  angularaxis: { tickfont: { size: 11 } },
                },
                showlegend: false,
                margin: { l: 50, r: 50, t: 20, b: 20 },
                height: 280,
              }}
            />
          </ChartCard>
        )}

        {cascadeLevels.length > 0 && (
          <ChartCard title="Cascade Distribution (Current vs Target)">
            <PlotlyChart
              data={[
                {
                  type: "bar",
                  name: "Current",
                  x: cascadeLevels,
                  y: currentPcts,
                  marker: { color: "#0D9488" },
                  hovertemplate: "Current %{x}: %{y:.1f}%<extra></extra>",
                },
                {
                  type: "bar",
                  name: "Target",
                  x: cascadeLevels,
                  y: targetPcts,
                  marker: { color: "#F59E0B" },
                  hovertemplate: "Target %{x}: %{y:.1f}%<extra></extra>",
                },
              ]}
              layout={{
                barmode: "group",
                xaxis: { title: { text: "Level" } },
                yaxis: { title: { text: "Spend %" }, ticksuffix: "%" },
                margin: { l: 50, r: 20, t: 20, b: 40 },
                height: 280,
                showlegend: true,
                legend: { orientation: "h", y: -0.25 },
              }}
            />
          </ChartCard>
        )}
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-surface rounded-lg border border-[#E5E5E0] p-5">
          <h4 className="text-xs font-semibold mb-4 uppercase tracking-[0.5px]">
            Improvement Recommendations
          </h4>
          <div className="space-y-3">
            {recommendations.map((rec, i) => (
              <div
                key={i}
                className="flex gap-3 p-3 bg-paper rounded-lg border border-[#F0F0EB]"
              >
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-tint text-[#0F766E] text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-medium">{rec.action}</span>
                    {rec.impact && (
                      <Badge
                        variant={
                          rec.impact === "high"
                            ? "red"
                            : rec.impact === "medium"
                            ? "amber"
                            : "slate"
                        }
                      >
                        {rec.impact}
                      </Badge>
                    )}
                  </div>
                  {rec.description && (
                    <p className="text-xs text-muted mt-1">{rec.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
