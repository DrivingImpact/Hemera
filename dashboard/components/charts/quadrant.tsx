"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";

const EFFORT_MAP: Record<string, number> = {
  low: 1,
  medium: 2,
  high: 3,
};

export function ImpactEffortQuadrant({
  recommendations,
}: {
  recommendations: {
    action: string;
    effort: string;
    potential_reduction_kg: number;
    type: string;
  }[];
}) {
  const xs = recommendations.map((r) => EFFORT_MAP[r.effort.toLowerCase()] ?? 2);
  const ys = recommendations.map((r) => r.potential_reduction_kg / 1000);
  const sizes = ys.map((y) => {
    const max = Math.max(...ys, 1);
    return 8 + (y / max) * 28;
  });
  const midY = ys.length > 0 ? (Math.min(...ys) + Math.max(...ys)) / 2 : 0;

  return (
    <PlotlyChart
      data={[
        {
          type: "scatter",
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          mode: "markers+text" as any,
          x: xs,
          y: ys,
          text: recommendations.map((r) =>
            r.action.length > 20 ? r.action.slice(0, 18) + "…" : r.action
          ),
          textposition: "top center",
          textfont: { size: 10 },
          marker: {
            size: sizes,
            color: "#0D9488",
            opacity: 0.75,
            line: { color: "#0F766E", width: 1 },
          },
          hovertemplate:
            "<b>%{text}</b><br>Effort: %{x}<br>Reduction: %{y:.1f} tCO₂e<extra></extra>",
          customdata: recommendations.map((r) => r.action),
        },
      ]}
      layout={{
        xaxis: {
          title: { text: "Effort", font: { size: 11 } },
          tickvals: [1, 2, 3],
          ticktext: ["Low", "Medium", "High"],
          range: [0.5, 3.5],
          tickfont: { size: 11 },
        },
        yaxis: {
          title: { text: "Reduction Potential (tCO₂e)", font: { size: 11 } },
          tickfont: { size: 11 },
        },
        shapes: [
          {
            type: "line",
            x0: 2,
            x1: 2,
            y0: 0,
            y1: 1,
            yref: "paper",
            line: { color: "#94A3B8", width: 1, dash: "dash" },
          },
          {
            type: "line",
            x0: 0,
            x1: 1,
            xref: "paper",
            y0: midY,
            y1: midY,
            line: { color: "#94A3B8", width: 1, dash: "dash" },
          },
        ],
        showlegend: false,
        margin: { l: 60, r: 20, t: 20, b: 50 },
        height: 320,
      }}
    />
  );
}
