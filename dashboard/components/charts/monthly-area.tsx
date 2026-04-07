"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { SCOPE_COLORS, SCOPE_LABELS } from "@/lib/plotly-theme";
import type { MonthlyData } from "@/lib/types";

interface MonthlyAreaProps {
  data: MonthlyData;
}

export function MonthlyArea({ data }: MonthlyAreaProps) {
  if (!data.has_data) {
    return (
      <div className="flex items-center justify-center h-40 text-muted text-sm">
        Insufficient date data to render monthly trend
      </div>
    );
  }

  const months = data.months.map((m) => m.month);

  const traces = [
    {
      type: "scatter" as const,
      mode: "lines" as const,
      fill: "tozeroy" as const,
      name: SCOPE_LABELS[1],
      x: months,
      y: data.months.map((m) => m.scope1),
      line: { color: SCOPE_COLORS[1], width: 2 },
      fillcolor: `${SCOPE_COLORS[1]}33`,
      hovertemplate: `${SCOPE_LABELS[1]}: %{y:.1f} tCO₂e<extra></extra>`,
    },
    {
      type: "scatter" as const,
      mode: "lines" as const,
      fill: "tonexty" as const,
      name: SCOPE_LABELS[2],
      x: months,
      y: data.months.map((m) => m.scope2),
      line: { color: SCOPE_COLORS[2], width: 2 },
      fillcolor: `${SCOPE_COLORS[2]}33`,
      hovertemplate: `${SCOPE_LABELS[2]}: %{y:.1f} tCO₂e<extra></extra>`,
    },
    {
      type: "scatter" as const,
      mode: "lines" as const,
      fill: "tonexty" as const,
      name: SCOPE_LABELS[3],
      x: months,
      y: data.months.map((m) => m.scope3),
      line: { color: SCOPE_COLORS[3], width: 2 },
      fillcolor: `${SCOPE_COLORS[3]}33`,
      hovertemplate: `${SCOPE_LABELS[3]}: %{y:.1f} tCO₂e<extra></extra>`,
    },
  ];

  return (
    <PlotlyChart
      data={traces}
      layout={{
        xaxis: { title: { text: "Month" }, tickangle: -30 },
        yaxis: { title: { text: "tCO₂e" } },
        margin: { l: 60, r: 20, t: 20, b: 60 },
        height: 300,
        showlegend: true,
        legend: { orientation: "h", y: -0.3 },
        hovermode: "x unified",
      }}
    />
  );
}
