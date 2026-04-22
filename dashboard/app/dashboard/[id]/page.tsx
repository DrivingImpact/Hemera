import { getEngagement, getCategories, getEngagementSuppliers } from "@/lib/api";
import { HeroBanner } from "@/components/ui/hero-banner";
import { ChartCard } from "@/components/ui/chart-card";
import { PendingBanner } from "@/components/ui/pending-banner";
import { ScopeDonut } from "@/components/charts/scope-donut";
import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { SCOPE_COLORS } from "@/lib/plotly-theme";
import { fmtTonnes, fmtGBP } from "@/lib/format";
import { ExcelDownloadButton } from "./excel-download-button";
import type { CategorySummary, EngagementSupplier } from "@/lib/types";

export default async function OverviewPage({
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
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm">No data yet.</p>
        </div>
      </div>
    );
  }

  if (engagement.status !== "qc_passed") {
    const pendingAnnotation = [{
      text: "Data pending",
      xref: "paper" as const, yref: "paper" as const,
      x: 0.5, y: 0.5,
      showarrow: false,
      font: { size: 14, color: "#94A3B8" },
    }];
    return (
      <div className="space-y-5">
        <HeroBanner engagement={engagement} pending />
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-[1.5fr_1fr] gap-4">
          <ChartCard title="Emissions by Scope" className="row-span-2">
            <PlotlyChart
              data={[{ type: "pie", hole: 0.6, values: [1], labels: [""], marker: { colors: ["#E5E5E0"] }, hoverinfo: "none", textinfo: "none" }]}
              layout={{ height: 250, showlegend: false, margin: { l: 20, r: 20, t: 20, b: 20 }, annotations: pendingAnnotation }}
            />
          </ChartCard>
          <ChartCard title="Top 5 Emission Hotspots">
            <PlotlyChart
              data={[{ type: "bar", orientation: "h" as const, x: [], y: [] }]}
              layout={{
                height: 180,
                xaxis: { title: { text: "tCO₂e" }, showticklabels: false },
                yaxis: { showticklabels: false },
                margin: { l: 10, r: 20, t: 10, b: 40 },
                annotations: pendingAnnotation,
              }}
            />
          </ChartCard>
          <ChartCard title="Supplier Risk Overview">
            <PlotlyChart
              data={[{ type: "bar", x: ["Low", "Medium", "High"], y: [0, 0, 0], marker: { color: ["#10B981", "#F59E0B", "#EF4444"] } }]}
              layout={{
                height: 180,
                xaxis: { title: { text: "Risk" } },
                yaxis: { title: { text: "Suppliers" }, showticklabels: false },
                margin: { l: 30, r: 20, t: 10, b: 40 },
                annotations: pendingAnnotation,
              }}
            />
          </ChartCard>
        </div>
      </div>
    );
  }

  const [categories, suppliers] = await Promise.all([
    getCategories(engagementId),
    getEngagementSuppliers(engagementId),
  ]);

  // Top 5 hotspots by co2e
  const topHotspots = [...categories]
    .sort((a, b) => b.co2e_tonnes - a.co2e_tonnes)
    .slice(0, 5);

  const maxCo2e = topHotspots[0]?.co2e_tonnes ?? 1;

  // Supplier risk counts based on intensity thresholds
  const riskCounts = suppliers.reduce(
    (acc: { low: number; medium: number; high: number }, s: EngagementSupplier) => {
      if (s.intensity_kg_per_gbp > 2) acc.high++;
      else if (s.intensity_kg_per_gbp > 0.5) acc.medium++;
      else acc.low++;
      return acc;
    },
    { low: 0, medium: 0, high: 0 }
  );

  const riskTotal = riskCounts.low + riskCounts.medium + riskCounts.high || 1;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <HeroBanner engagement={engagement} />
        <ExcelDownloadButton engagementId={engagementId} orgName={engagement.org_name} />
      </div>

      <div className="grid grid-cols-[1.5fr_1fr] gap-4">
        {/* Left: Scope donut (row-span-2) */}
        <ChartCard
          title="Emissions by Scope"
          className="row-span-2"
          linkHref={`/dashboard/${id}/carbon`}
          linkText="View carbon breakdown →"
        >
          <ScopeDonut
            scope1={engagement.scope1_co2e}
            scope2={engagement.scope2_co2e}
            scope3={engagement.scope3_co2e}
          />
        </ChartCard>

        {/* Top right: Top 5 hotspots */}
        <ChartCard
          title="Top 5 Emission Hotspots"
          linkHref={`/dashboard/${id}/carbon`}
          linkText="View all categories →"
        >
          <div className="space-y-2 mt-2">
            {topHotspots.map((cat: CategorySummary) => {
              const pct = (cat.co2e_tonnes / maxCo2e) * 100;
              const color = SCOPE_COLORS[cat.scope] ?? "#64748B";
              return (
                <div key={cat.name}>
                  <div className="flex justify-between text-[12px] mb-0.5">
                    <span className="truncate max-w-[60%] font-medium" title={cat.name}>
                      {cat.name}
                    </span>
                    <span className="tabular-nums text-muted">
                      {fmtTonnes(cat.co2e_tonnes)} tCO₂e
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-[#F0F0EB] overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>

        {/* Bottom right: Supplier risk overview */}
        <ChartCard
          title="Supplier Risk Overview"
          linkHref={`/dashboard/${id}/suppliers`}
          linkText="View all suppliers →"
        >
          <div className="space-y-2 mt-2">
            {[
              { label: "Low Risk", count: riskCounts.low, color: "#10B981", bg: "#D1FAE5" },
              { label: "Medium Risk", count: riskCounts.medium, color: "#F59E0B", bg: "#FEF3C7" },
              { label: "High Risk", count: riskCounts.high, color: "#EF4444", bg: "#FEE2E2" },
            ].map(({ label, count, color, bg }) => {
              const pct = (count / riskTotal) * 100;
              return (
                <div key={label}>
                  <div className="flex justify-between text-[12px] mb-0.5">
                    <span className="font-medium">{label}</span>
                    <span className="tabular-nums text-muted">{count} suppliers</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#F0F0EB] overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, backgroundColor: color, background: bg }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 pt-2 border-t border-[#F0F0EB]">
            <div className="text-[11px] text-muted">
              Total spend tracked: {fmtGBP(suppliers.reduce((s: number, sup: EngagementSupplier) => s + sup.spend_gbp, 0))}
            </div>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
