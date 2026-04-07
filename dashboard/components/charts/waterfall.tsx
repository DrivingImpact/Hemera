"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { fmtTonnes } from "@/lib/format";

export function ReductionWaterfall({
  baseline,
  reductions,
}: {
  baseline: number;
  reductions: { action: string; reduction_tonnes: number }[];
}) {
  const target = baseline - reductions.reduce((sum, r) => sum + r.reduction_tonnes, 0);

  const x = [
    "Current",
    ...reductions.map((r) => r.action),
    "Target",
  ];

  const y = [
    baseline,
    ...reductions.map((r) => r.reduction_tonnes),
    target,
  ];

  const measure: string[] = [
    "absolute",
    ...reductions.map(() => "relative"),
    "total",
  ];

  return (
    <PlotlyChart
      data={[
        {
          type: "waterfall" as const,
          orientation: "v",
          x,
          y,
          measure,
          decreasing: { marker: { color: "#0D9488" } },
          totals: { marker: { color: "#1E293B" } },
          increasing: { marker: { color: "#EF4444" } },
          connector: { line: { color: "#94A3B8", width: 1, dash: "dot" } },
          textposition: "outside",
          text: y.map((v) => `${fmtTonnes(v)}t`),
          hovertemplate: "<b>%{x}</b><br>%{y:.1f} tCO₂e<extra></extra>",
        },
      ]}
      layout={{
        showlegend: false,
        xaxis: {
          tickfont: { size: 11 },
          tickangle: -30,
        },
        yaxis: {
          title: { text: "tCO₂e", font: { size: 11 } },
          tickfont: { size: 11 },
        },
        margin: { l: 60, r: 20, t: 20, b: 80 },
        height: 320,
      }}
    />
  );
}
